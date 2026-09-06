import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether, PageBreak
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        
        # Header (pages 2+)
        if self._pageNumber > 1:
            self.drawString(54, 750, "MemoryVault AI — Team Technical & Operational Briefing Guide")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(54, 742, 558, 742)
        
        # Footer (all pages)
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(54, 45, 558, 45)
        
        self.setFont("Helvetica", 8)
        self.drawString(54, 32, "Confidential — For Team Internal Briefing & Presentation Prep")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 32, page_str)
        self.restoreState()

def build_pdf(filename="MemoryVault_AI_Team_Presentation_Briefing.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )
    
    styles = getSampleStyleSheet()
    
    # Custom Palette
    c_primary = colors.HexColor("#0f172a")    # Slate 900
    c_brand = colors.HexColor("#0284c7")      # Sky 600
    c_accent = colors.HexColor("#0369a1")     # Deep Sky
    c_body = colors.HexColor("#1e293b")       # Slate 800
    c_bg_light = colors.HexColor("#f8fafc")   # Slate 50
    c_border = colors.HexColor("#e2e8f0")     # Slate 200

    # Custom Typography Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=c_primary,
        spaceAfter=4
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=c_brand,
        spaceAfter=15
    )

    h1_style = ParagraphStyle(
        'SectionH1',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=c_primary,
        spaceBefore=14,
        spaceAfter=8,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=c_accent,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
        textColor=c_body,
        spaceAfter=6
    )

    bullet_style = ParagraphStyle(
        'BulletText',
        parent=body_style,
        leftIndent=14,
        spaceAfter=4
    )

    code_style = ParagraphStyle(
        'CodeStyle',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#0f172a"),
        backColor=colors.HexColor("#f1f5f9"),
        borderColor=colors.HexColor("#cbd5e1"),
        borderWidth=0.5,
        borderPadding=6,
        spaceBefore=4,
        spaceAfter=6
    )

    story = []

    # -------------------------------------------------------------------------
    # COVER / HEADER TITLE
    # -------------------------------------------------------------------------
    story.append(Paragraph("MemoryVault AI — Complete Team Briefing", title_style))
    story.append(Paragraph("Comprehensive Technical Architecture, ML Models, Algorithms, Tech Stack & Terminal Run Guide", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=c_brand, spaceBefore=0, spaceAfter=12))

    # -------------------------------------------------------------------------
    # 1. EXECUTIVE SUMMARY & PROJECT DESCRIPTION
    # -------------------------------------------------------------------------
    story.append(Paragraph("1. Executive Summary & Project Description", h1_style))
    story.append(Paragraph(
        "<b>MemoryVault AI</b> is an intelligent, context-aware web application designed to solve a universal daily friction: <b>misplacing everyday essential items</b> (such as car keys, wallets, passports, reading glasses, and wireless earbuds).",
        body_style
    ))
    story.append(Paragraph(
        "Instead of relying on random searching or manual Bluetooth hardware tags (AirTags/Tile) which require battery maintenance and prior attachment, MemoryVault AI leverages <b>Machine Learning (Habit Profiling)</b> and <b>Graph Search Routing (A* Pathfinding)</b> to predict exact locations based on human situational context.",
        body_style
    ))
    
    # Key Value Props Box
    key_props = [
        [Paragraph("<b>Core Problem Solved:</b> Replaces chaotic, frantic searching with a mathematically optimal, room-by-room search sequence checklist.", body_style)],
        [Paragraph("<b>Key Innovation:</b> Combines Machine Learning probabilistic classification (Random Forest + Gradient Boosting) with spatial layout graph search (A*) to minimize walking time.", body_style)]
    ]
    t_props = Table(key_props, colWidths=[504])
    t_props.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f0f9ff")),
        ('BORDER', (0,0), (-1,-1), 1, colors.HexColor("#bae6fd")),
        ('PADDING', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_props)
    story.append(Spacer(1, 10))

    # -------------------------------------------------------------------------
    # 2. END-TO-END SYSTEM WORKFLOW
    # -------------------------------------------------------------------------
    story.append(Paragraph("2. End-to-End Operational Workflow", h1_style))
    story.append(Paragraph(
        "The application operates through a seamless 4-stage pipeline:",
        body_style
    ))
    
    workflow_steps = [
        "<b>Stage 1: Conversational Triage (Slot-Filling State Machine)</b><br/>The user interacts with an AI assistant on the left Chat Pane. The system progressively collects context (target item, time of day, routine disruption, emotional state, last activity).",
        "<b>Stage 2: Context Feature Extraction & ML Habit Profiling</b><br/>Context inputs are normalized and fed into the trained ML Ensemble Model to calculate room probability distributions across 8 household rooms.",
        "<b>Stage 3: Spatial Graph Routing (Modified A* Heuristic)</b><br/>The A* Search Router calculates edge walking distances and prioritizes high-probability locations to produce an expected-search-time-optimized route.",
        "<b>Stage 4: Interactive Blueprint & Route Inspector</b><br/>The right pane renders an architectural blueprint floor plan with neon search paths, step sequence badges (#1, #2), distance pills, and an expandable HD modal."
    ]
    for step in workflow_steps:
        story.append(Paragraph(f"• {step}", bullet_style))

    story.append(Spacer(1, 10))

    # -------------------------------------------------------------------------
    # 3. DATASET & MACHINE LEARNING ALGORITHMS
    # -------------------------------------------------------------------------
    story.append(Paragraph("3. Synthetic Dataset & ML Algorithms", h1_style))
    story.append(Paragraph("<b>3.1 Synthetic Habit Dataset Overview</b>", h2_style))
    story.append(Paragraph(
        "The ML models are trained on a synthetic dataset of <b>5,000 contextual habit records</b> generated via probabilistic distribution sampling. Features include: <i>item_type</i>, <i>time_of_day</i>, <i>day_type</i> (weekday/weekend), <i>stress_level</i> (low/medium/high), <i>has_guests</i> (boolean), <i>routine_disrupted</i> (boolean), and <i>last_activity</i> (cooking, working, resting, entering home, rushing).",
        body_style
    ))

    story.append(Paragraph("<b>3.2 Machine Learning Algorithms & Mathematical Role</b>", h2_style))
    
    ml_table_data = [
        [Paragraph("<b>Algorithm</b>", body_style), Paragraph("<b>Function & How It Works</b>", body_style), Paragraph("<b>Problem Solved</b>", body_style)],
        [
            Paragraph("<b>Random Forest Classifier</b>", body_style),
            Paragraph("Ensemble of 100 decision trees computing non-linear feature splits across contextual variables to output location probabilities.", body_style),
            Paragraph("Prevents overfitting and handles complex non-linear habit interactions.", body_style)
        ],
        [
            Paragraph("<b>Gradient Boosting Classifier</b>", body_style),
            Paragraph("Sequential boosting decision tree ensemble that iteratively minimizes residual loss on hard-to-predict contextual edge cases.", body_style),
            Paragraph("Boosts accuracy for high-stress or disrupted routine edge cases.", body_style)
        ],
        [
            Paragraph("<b>K-Means & PCA Clustering</b>", body_style),
            Paragraph("K-Means groups contextual vectors into habit clusters; Principal Component Analysis (PCA) projects 8D feature space into 2D scatter coordinates.", body_style),
            Paragraph("Provides visual habit cluster insights in the Evaluator Analytics drawer.", body_style)
        ]
    ]
    t_ml = Table(ml_table_data, colWidths=[110, 244, 150])
    t_ml.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0f172a")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(t_ml)
    story.append(Spacer(1, 10))

    # -------------------------------------------------------------------------
    # 4. SPATIAL ROUTING ALGORITHM (A*)
    # -------------------------------------------------------------------------
    story.append(Paragraph("4. Spatial Search Router (A* Pathfinding)", h1_style))
    story.append(Paragraph(
        "<b>A* Graph Search Heuristic</b>: Traditional shortest-path A* finds the shortest geometric path. MemoryVault AI utilizes a modified cost function that balances <i>walking distance in meters</i> against <i>room item probability</i>:",
        body_style
    ))
    story.append(Paragraph(
        "$$\\text{Cost}(v_{i-1} \\to v_i) = \\frac{\\text{Distance}(v_{i-1}, v_i)}{P(v_i) + \\epsilon}$$",
        code_style
    ))
    story.append(Paragraph(
        "<b>What Problem It Solves:</b> Searching room A then room B across the house can waste significant time if a medium-probability room is directly on the way. A* pathfinding computes the single most time-efficient room sequence starting from the main entrance.",
        body_style
    ))

    story.append(Spacer(1, 10))

    # -------------------------------------------------------------------------
    # 5. COMPLETE TECH STACK & LIBRARIES USED
    # -------------------------------------------------------------------------
    story.append(Paragraph("5. Technology Stack & Library Breakdown", h1_style))
    
    tech_table_data = [
        [Paragraph("<b>Component Layer</b>", body_style), Paragraph("<b>Technologies & Libraries</b>", body_style), Paragraph("<b>Purpose</b>", body_style)],
        [
            Paragraph("<b>Backend Server</b>", body_style),
            Paragraph("<b>Python 3.10+, FastAPI, Uvicorn, Pydantic</b>", body_style),
            Paragraph("Asynchronous REST API framework for fast request processing and OpenAPI documentation.", body_style)
        ],
        [
            Paragraph("<b>Machine Learning</b>", body_style),
            Paragraph("<b>Scikit-Learn, Joblib, Pandas, NumPy</b>", body_style),
            Paragraph("Model training, pipeline serialization, metrics calculation, and feature encoding.", body_style)
        ],
        [
            Paragraph("<b>Frontend Framework</b>", body_style),
            Paragraph("<b>Next.js 16 (Turbopack), React 19, TypeScript</b>", body_style),
            Paragraph("Server-side rendering, component-driven UI architecture, and fast client-side state management.", body_style)
        ],
        [
            Paragraph("<b>Styling & Icons</b>", body_style),
            Paragraph("<b>Vanilla CSS (Tokens), TailwindCSS, Lucide-React</b>", body_style),
            Paragraph("Custom dark-theme blueprint design system, responsive split-pane, and crisp icons.", body_style)
        ],
        [
            Paragraph("<b>Graphics & Blueprint</b>", body_style),
            Paragraph("<b>SVG (Scalable Vector Graphics), HTML5 Canvas</b>", body_style),
            Paragraph("High-contrast architectural floor plan map, neon A* paths, Confusion Matrix & ROC curves.", body_style)
        ]
    ]
    t_tech = Table(tech_table_data, colWidths=[110, 214, 180])
    t_tech.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0284c7")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(t_tech)
    story.append(Spacer(1, 14))

    # Page Break for clean Command Reference section
    story.append(PageBreak())

    # -------------------------------------------------------------------------
    # 6. TERMINAL RUN & STOP COMMANDS (FOR TEAM MEMBERS)
    # -------------------------------------------------------------------------
    story.append(Paragraph("6. Terminal Run & Stop Commands (Step-by-Step)", h1_style))
    story.append(Paragraph(
        "Team members can follow these exact commands in 2 separate terminal windows to run and test the project locally.",
        body_style
    ))

    # Terminal 1: Backend
    story.append(Paragraph("<b>Terminal #1: Backend (FastAPI Python Server)</b>", h2_style))
    story.append(Paragraph("<b>Exact Target Folder Path:</b> <code>C:\\Users\\parab\\OneDrive\\Desktop\\Projects\\Memory_vault-ai\\memoryvault-ai\\backend</code>", body_style))
    
    cmd_backend = (
        "# 1. Navigate to backend folder\n"
        "cd backend\n\n"
        "# 2. Install dependencies (First time only)\n"
        "pip install -r requirements.txt\n\n"
        "# 3. Train ML Models & compute metrics\n"
        "python -m app.ml.train\n\n"
        "# 4. Launch FastAPI Server\n"
        "python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
    )
    story.append(Paragraph(cmd_backend.replace('\n', '<br/>'), code_style))

    # Terminal 2: Frontend
    story.append(Paragraph("<b>Terminal #2: Frontend (Next.js Application)</b>", h2_style))
    story.append(Paragraph("<b>Exact Target Folder Path:</b> <code>C:\\Users\\parab\\OneDrive\\Desktop\\Projects\\Memory_vault-ai\\memoryvault-ai\\frontend</code>", body_style))
    
    cmd_frontend = (
        "# 1. Navigate to frontend folder\n"
        "cd frontend\n\n"
        "# 2. Install npm packages (First time only)\n"
        "npm install\n\n"
        "# 3. Launch Next.js Dev Server\n"
        "npm run dev"
    )
    story.append(Paragraph(cmd_frontend.replace('\n', '<br/>'), code_style))

    story.append(Paragraph("<b>Browser Access URL:</b> 👉 Open <b>http://localhost:3000</b> in your browser.", body_style))

    story.append(Spacer(1, 8))

    # Stop Commands
    story.append(Paragraph("<b>How to Stop the Project</b>", h2_style))
    story.append(Paragraph("• <b>Method 1 (Keyboard):</b> Press <code>Ctrl + C</code> in both terminal windows.", bullet_style))
    story.append(Paragraph("• <b>Method 2 (PowerShell Command):</b> Run the following commands to forcefully kill ports 3000 and 8000:", bullet_style))
    
    cmd_stop = (
        "# Stop Frontend on Port 3000\n"
        "Get-Process -Id (Get-NetTCPConnection -LocalPort 3000).OwningProcess -ErrorAction SilentlyContinue | Stop-Process -Force\n\n"
        "# Stop Backend on Port 8000\n"
        "Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess -ErrorAction SilentlyContinue | Stop-Process -Force"
    )
    story.append(Paragraph(cmd_stop.replace('\n', '<br/>'), code_style))

    story.append(Spacer(1, 10))

    # -------------------------------------------------------------------------
    # 7. PRESENTATION TALKING POINTS & DEMO SCRIPT
    # -------------------------------------------------------------------------
    story.append(Paragraph("7. Key Presentation Talking Points & Live Demo Guide", h1_style))
    
    demo_points = [
        "<b>1. Introduce the Hook (30 sec):</b> Ask the audience/judges: <i>'How many times have you wasted 15 minutes searching for your car keys or wallet before leaving home?'</i>",
        "<b>2. Explain MemoryVault AI Solution (45 sec):</b> Highlight that MemoryVault AI replaces blind panic with ML habit predictions and A* pathfinding.",
        "<b>3. Live Demo Flow (2 min):</b><br/>"
        "   a. Open <code>http://localhost:3000</code>.<br/>"
        "   b. Select <b>Car Keys</b> and answer the quick-reply prompts (e.g. Evening, Rushing, High Stress).<br/>"
        "   c. Show the <b>Search Route Inspector</b> blueprint map updated automatically with neon paths, distance markers (meters), and step badges (#1, #2).<br/>"
        "   d. Click <b>'Expand Map'</b> to showcase the HD Fullscreen architectural modal.<br/>"
        "   e. Click <b>'Evaluator Analytics'</b> in the top right to demonstrate model accuracy, confusion matrix, and ROC curves.<br/>"
        "   f. Click <b>'Search Another Item'</b> to demonstrate instant session reset for a second item (e.g. Wallet or Passport).",
        "<b>4. Summary & Q&A Prep (30 sec):</b> Reiterate that the app uses real spatial graph optimization and self-learning feedback loops when the user clicks 'Found Here'."
    ]
    for p in demo_points:
        story.append(Paragraph(f"• {p}", bullet_style))

    # Build Document with Numbered Canvas
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated {filename}")

if __name__ == "__main__":
    build_pdf()
