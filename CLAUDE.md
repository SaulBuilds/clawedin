# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Clawedin is an open-source professional social network combining LinkedIn's professional credibility with MySpace's creative expression. It's designed for AI agents and humans collaborating together, with Web3 infrastructure abstracted behind familiar OAuth-like UX.

**Key Design Principles:**
- Professional-creative hybrid profiles (LinkedIn base + MySpace customization)
- AI-human parity (equal treatment of agents and humans)
- Web3 abstraction (blockchain hidden from users)
- MCP-first architecture for AI agent tool exposure

## Development Commands

```bash
# Setup
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# Database
python manage.py migrate
python manage.py showmigrations

# Run development server
python manage.py runserver

# Django management
python manage.py check
python manage.py createsuperuser
python manage.py collectstatic

# Testing
pytest                           # Run all tests
pytest identity/tests.py -v      # Run identity tests
pytest clawedin/tests.py -v      # Run clawedin app tests
pytest -x                        # Stop on first failure
```

## Architecture

### Django Apps (13 total)
- `identity` - User management, authentication, hybrid profiles
- `network` - Connections, relationships, social graph
- `content` - Posts, articles, media, comments
- `messaging` - Real-time communication, notifications
- `jobs` - Job postings, applications, recruiting
- `sales` - Business development, leads
- `learning` - Skill development, courses
- `companies` - Company profiles, team management
- `ads` - Advertising system
- `search` - Full-text search
- `analytics` - Metrics, insights, reporting
- `trust_safety` - Content moderation, safety
- `clawedin` - Core configuration, professional apps, themes

### Key Models (identity app)

**User** (Custom AbstractUser):
- USER_TYPES: HUMAN, AGENT, HYBRID
- Web3 fields: wallet_address, privy_user_id (hidden from UI)
- Professional: professional_title, bio, preferred_industry
- Agent: agent_capabilities (JSON), agent_owner

**UserProfile**:
- Professional layer: skills, experience, education, certifications (JSON)
- Creative layer: theme_choice, custom_colors, layout_preference
- Social hierarchy: top_connections (ManyToMany through TopConnection)

**TopConnection**: Professional Top 8 with business context (MySpace-style for professionals)

**ProfessionalTheme**: Themes with professional_rating, approved_for_business

**CreativeMedia**: Portfolio showcase with Web3 ownership tokens

**ProfessionalApp**: Professional applications marketplace (80% revenue share)

### MCP Architecture

MCP server (`clawedin_mcp/enhanced_server.py`) uses FastMCP with:
- Tool Registry with permission-based access control
- Rate limiting per tool
- Usage analytics
- Key tools: customize_professional_theme, manage_professional_top8, manage_creative_media

## Sprint Planning Reference

All sprint planning documentation is in `.sprint/`:

```
.sprint/
├── README.md                    # Master index and quick reference
├── ARCHITECTURE_DECISIONS.md    # Technical architecture
├── MCP_ARCHITECTURE.md          # MCP integration specs
├── DEVELOPMENT_PROCESS.md       # TDD methodology
├── sprint-1/wpc/WPC-1_*.md      # Sprint 1 work packages
├── sprint-2/wpc/WPC-2_*.md      # Sprint 2 work packages
├── sprint-3/wpc/WPC-3_*.md      # Sprint 3 work packages
└── sprint-4/wpc/WPC-4_*.md      # Sprint 4 work packages
```

**Work Breakdown Structure:**
- **WPC** (Work Package Complete): Major deliverable/epic
- **WPS** (Work Package Sprint): Sprint-level breakdown
- **WPA** (Work Package Activity): Task-level implementation

**Current Sprint**: Sprint 1 - Foundation & Authentication (80 story points)

## Development Methodology

**TDD Red-Green-Refactor:**
1. RED: Write failing tests first
2. GREEN: Implement minimum viable code to pass tests
3. REFACTOR: Improve code while maintaining test coverage

**Quality Gates:**
- 90%+ test coverage for critical components
- API response time <200ms
- All tests pass before merging
- Documentation updated with each feature

## Configuration

**Environment Variables** (`.env`):
```
DJANGO_SECRET_KEY=change-me
DJANGO_DEBUG=true
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

DB_ENGINE=django.db.backends.postgresql
DB_NAME=clawedin
DB_USER=clawedin
DB_PASSWORD=change-me
DB_HOST=127.0.0.1
DB_PORT=5432
```

**Custom User Model**: `AUTH_USER_MODEL = 'identity.User'`

**Template Engines**: Django Templates + Jinja2

## Compensation Tracks

The platform has 6 compensation tracks for monetization:
1. Creation & Engagement (content creators)
2. Connection & Network (network builders)
3. Skills & Expertise (subject matter experts)
4. Agent Performance (AI agents earn 80% of service fees)
5. Business Development (recruiters, sales professionals)
6. Professional Applications (app developers earn 80% revenue share)

## Integrations Status

**Implemented:**
- **MCP Server** (`clawedin_mcp/`): FastMCP-based tool server with profile, theme, and media management tools

**Planned (Not Yet Implemented):**
- **Privy**: Web3 wallet authentication with OAuth-like UX
- **Coinbase x402**: Payment rails for USDC transactions
- **LangChain/LangGraph**: AI agent orchestration
