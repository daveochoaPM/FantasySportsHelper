import azure.functions as func
import json
import os
import datetime as dt
from libs import cosmos
from libs.yahoo_client import YahooClient
from libs.nhl_client import fetch_schedule, season_code
from engine.guidance import compute_guidance, tl_dr
from engine.llm import rewrite
from jinja2 import Template
import base64
import io
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors

def main(req: func.HttpRequest) -> func.HttpResponse:
    # Check for admin role in headers (set by Azure Static Web Apps)
    user_roles = req.headers.get('x-ms-client-principal-roles', '')
    if 'admin' not in user_roles:
        return func.HttpResponse("Unauthorized: Admin role required", status_code=403)
    
    if req.method != "POST":
        return func.HttpResponse("Method not allowed", status_code=405)
    
    try:
        data = req.get_json()
        league_id = data.get("leagueId")
        week = data.get("week", 1)
        title = data.get("title", f"Week {week} Fantasy Report")
        format_type = data.get("format", "html")
        include_rosters = data.get("includeRosters", True)
        include_schedule = data.get("includeSchedule", True)
        include_stats = data.get("includeStats", True)
        include_guidance = data.get("includeGuidance", True)
        
        if not league_id:
            return func.HttpResponse("Missing leagueId", status_code=400)
        
        # Get league information
        league_doc = cosmos.get("leagues", f"league-{league_id}", partition=league_id)
        if not league_doc:
            return func.HttpResponse("League not found", status_code=404)
        
        # Get all managers for this league
        managers = cosmos.query("managers", f"SELECT * FROM c WHERE c.leagueId = '{league_id}'")
        
        if not managers:
            return func.HttpResponse("No managers found for this league", status_code=404)
        
        # Initialize Yahoo client
        yahoo_client = YahooClient()
        
        # Get league data
        league_data = yahoo_client.get_league(league_id)
        teams = league_data.get('teams', [])
        
        # Generate reports for each team
        reports = []
        total_teams = len(teams)
        generated_reports = 0
        failed_reports = 0
        
        for i, team in enumerate(teams):
            try:
                team_id = team.get('team_id')
                team_name = team.get('name', f"Team {team_id}")
                
                # Find manager for this team
                manager = next((m for m in managers if m['teamId'] == str(team_id)), None)
                manager_name = manager.get('name', 'Unknown') if manager else 'Unknown'
                manager_email = manager.get('email', '') if manager else ''
                
                # Get team roster
                roster = yahoo_client.get_roster(league_id, team_id, week) if include_rosters else []
                
                # Get NHL schedule for the week
                schedule = fetch_schedule(week) if include_schedule else []
                
                # Generate guidance for this team
                guidance = []
                if include_guidance:
                    try:
                        guidance = compute_guidance(league_id, team_id, week)
                    except Exception as e:
                        guidance = [{"type": "error", "message": f"Guidance generation failed: {str(e)}"}]
                
                # Create team report
                team_report = {
                    "team_id": team_id,
                    "team_name": team_name,
                    "manager_name": manager_name,
                    "manager_email": manager_email,
                    "week": week,
                    "roster": roster if include_rosters else [],
                    "schedule": schedule if include_schedule else [],
                    "guidance": guidance if include_guidance else [],
                    "league_name": league_data.get('name', f"League {league_id}"),
                    "generated_at": dt.datetime.now().isoformat()
                }
                
                reports.append(team_report)
                generated_reports += 1
                
            except Exception as e:
                failed_reports += 1
                # Add error report
                reports.append({
                    "team_id": team.get('team_id', 'unknown'),
                    "team_name": team.get('name', 'Unknown Team'),
                    "error": str(e),
                    "generated_at": dt.datetime.now().isoformat()
                })
        
        # Get the current logo
        logo_url = get_current_logo()
        
        # Generate report content based on format
        if format_type == "pdf":
            # Generate PDF report
            pdf_content = generate_pdf_report(reports, title, league_id, week, logo_url)
            report_doc = {
                "id": f"report-{league_id}-{week}-{int(dt.datetime.now().timestamp())}",
                "leagueId": league_id,
                "week": week,
                "title": title,
                "format": "pdf",
                "totalTeams": total_teams,
                "generatedReports": generated_reports,
                "failedReports": failed_reports,
                "createdAt": dt.datetime.now().isoformat(),
                "pdfContent": pdf_content
            }
        else:
            # Generate HTML report
            html_content = generate_html_report(reports, title, league_id, week, logo_url)
            report_doc = {
                "id": f"report-{league_id}-{week}-{int(dt.datetime.now().timestamp())}",
                "leagueId": league_id,
                "week": week,
                "title": title,
                "format": "html",
                "totalTeams": total_teams,
                "generatedReports": generated_reports,
                "failedReports": failed_reports,
                "createdAt": dt.datetime.now().isoformat(),
                "htmlContent": html_content
            }
        
        cosmos.upsert("reports", report_doc, partition=league_id)
        
        # Return success response
        return func.HttpResponse(json.dumps({
            "message": "Reports generated successfully",
            "totalTeams": total_teams,
            "generatedReports": generated_reports,
            "failedReports": failed_reports,
            "downloadUrl": f"/api/admin/reports/{report_id}/download",
            "printUrl": f"/api/admin/reports/{report_id}/print",
            "reportId": report_id
        }), status_code=200, mimetype="application/json")
        
    except Exception as e:
        return func.HttpResponse(json.dumps({
            "error": f"Report generation failed: {str(e)}"
        }), status_code=500, mimetype="application/json")

def get_current_logo():
    """Get the most recent logo from storage"""
    try:
        logos = cosmos.query("logos", "SELECT * FROM c ORDER BY c.uploadedAt DESC")
        if logos:
            return logos[0].get("blobUrl", "")
    except:
        pass
    return ""

def generate_pdf_report(reports, title, league_id, week, logo_url):
    """Generate PDF report with professional formatting"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=1*inch, bottomMargin=1*inch)
    
    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=1,  # Center alignment
        textColor=colors.darkblue
    )
    
    team_style = ParagraphStyle(
        'TeamName',
        parent=styles['Heading2'],
        fontSize=18,
        spaceAfter=20,
        alignment=1,  # Center alignment
        textColor=colors.darkgreen
    )
    
    guidance_style = ParagraphStyle(
        'Guidance',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=12,
        leftIndent=20,
        bulletIndent=10
    )
    
    # Build the story (content)
    story = []
    
    # Add logo if available
    if logo_url:
        try:
            logo = Image(logo_url, width=3*inch, height=1*inch)
            logo.hAlign = 'CENTER'
            story.append(logo)
            story.append(Spacer(1, 20))
        except:
            pass  # Continue without logo if there's an error
    
    # Add title
    story.append(Paragraph(title, title_style))
    story.append(Spacer(1, 20))
    
    # Add each team's report
    for report in reports:
        if report.get('error'):
            # Add error page
            story.append(Paragraph(f"<b>{report['team_name']}</b>", team_style))
            story.append(Paragraph(f"Error: {report['error']}", styles['Normal']))
            story.append(Spacer(1, 20))
        else:
            # Add team name
            story.append(Paragraph(f"<b>{report['team_name']}</b>", team_style))
            
            # Add manager info
            if report.get('manager_name'):
                story.append(Paragraph(f"Manager: {report['manager_name']}", styles['Normal']))
            
            # Add guidance/recommendations
            if report.get('guidance'):
                story.append(Paragraph("<b>Fantasy Recommendations:</b>", styles['Heading3']))
                for item in report['guidance']:
                    if item.get('message'):
                        story.append(Paragraph(f"• {item['message']}", guidance_style))
            
            # Add roster info if available
            if report.get('roster') and len(report['roster']) > 0:
                story.append(Paragraph("<b>Current Roster:</b>", styles['Heading3']))
                roster_text = ", ".join([f"{player.get('name', 'Unknown')} ({player.get('position', 'N/A')})" for player in report['roster'][:10]])
                if len(report['roster']) > 10:
                    roster_text += f" and {len(report['roster']) - 10} more players"
                story.append(Paragraph(roster_text, styles['Normal']))
            
            story.append(Spacer(1, 30))  # Space between teams
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    
    # Convert to base64 for storage
    pdf_content = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return pdf_content

def generate_html_report(reports, title, league_id, week, logo_url):
    """Generate HTML report with one page per team"""
    
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>{{ title }}</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
            .page { page-break-after: always; margin-bottom: 40px; }
            .page:last-child { page-break-after: avoid; }
            .header { text-align: center; margin-bottom: 30px; border-bottom: 2px solid #007cba; padding-bottom: 10px; }
            .logo { max-width: 300px; max-height: 100px; margin-bottom: 20px; }
            .team-info { background: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
            .roster { margin-bottom: 20px; }
            .roster table { width: 100%; border-collapse: collapse; }
            .roster th, .roster td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            .roster th { background: #007cba; color: white; }
            .guidance { background: #e6f3ff; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
            .guidance h3 { color: #007cba; margin-top: 0; }
            .guidance ul { margin: 10px 0; }
            .schedule { margin-bottom: 20px; }
            .schedule table { width: 100%; border-collapse: collapse; }
            .schedule th, .schedule td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            .schedule th { background: #28a745; color: white; }
            .error { background: #f8d7da; color: #721c24; padding: 15px; border-radius: 5px; }
            .footer { text-align: center; margin-top: 30px; font-size: 12px; color: #666; }
        </style>
    </head>
    <body>
        <div class="header">
            {% if logo_url %}
            <img src="{{ logo_url }}" alt="League Logo" class="logo">
            {% endif %}
            <h1>{{ title }}</h1>
            <p>League: {{ league_name }} | Week: {{ week }}</p>
            <p>Generated: {{ generated_at }}</p>
        </div>
        
        {% for report in reports %}
        <div class="page">
            <div class="team-info">
                <h2>{{ report.team_name }}</h2>
                <p><strong>Manager:</strong> {{ report.manager_name }}</p>
                {% if report.manager_email %}
                <p><strong>Email:</strong> {{ report.manager_email }}</p>
                {% endif %}
            </div>
            
            {% if report.error %}
            <div class="error">
                <h3>❌ Error Generating Report</h3>
                <p>{{ report.error }}</p>
            </div>
            {% else %}
            
            {% if report.roster %}
            <div class="roster">
                <h3>📊 Current Roster</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Player</th>
                            <th>Position</th>
                            <th>Team</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for player in report.roster %}
                        <tr>
                            <td>{{ player.name }}</td>
                            <td>{{ player.position }}</td>
                            <td>{{ player.team }}</td>
                            <td>{{ player.status }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            {% endif %}
            
            {% if report.schedule %}
            <div class="schedule">
                <h3>📅 NHL Schedule This Week</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Date</th>
                            <th>Home Team</th>
                            <th>Away Team</th>
                            <th>Time</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for game in report.schedule %}
                        <tr>
                            <td>{{ game.date }}</td>
                            <td>{{ game.home_team }}</td>
                            <td>{{ game.away_team }}</td>
                            <td>{{ game.time }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            {% endif %}
            
            {% if report.guidance %}
            <div class="guidance">
                <h3>🎯 Fantasy Guidance</h3>
                <ul>
                    {% for item in report.guidance %}
                    <li>{{ item.message }}</li>
                    {% endfor %}
                </ul>
            </div>
            {% endif %}
            
            {% endif %}
            
            <div class="footer">
                <p>Fantasy Sports Helper - Generated {{ report.generated_at }}</p>
            </div>
        </div>
        {% endfor %}
    </body>
    </html>
    """
    
    template = Template(html_template)
    return template.render(
        title=title,
        league_name=f"League {league_id}",
        week=week,
        generated_at=dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        logo_url=logo_url,
        reports=reports
    )
