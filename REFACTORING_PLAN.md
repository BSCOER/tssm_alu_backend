# Backend Refactoring Plan

## Overview
Converting monolithic `app.py` (4000+ lines) into a modular, maintainable structure.

## New Structure

```
backend/tssm_alu_backend/
├── app.py                          # Main application factory
├── config.py                       # Configuration settings ✓
├── extensions.py                   # Flask extensions ✓
├── database.py                     # Database connection ✓
├── requirements.txt                # Dependencies (existing)
├── runtime.txt                     # Runtime (existing)
├── utils/                          # Utility functions
│   ├── __init__.py                 # ✓
│   ├── helpers.py                  # Serialization, enrichment ✓
│   ├── decorators.py               # Auth decorators ✓
│   └── notifications.py            # Mention notifications ✓
├── services/                       # Business logic services
│   ├── __init__.py                 # ✓
│   ├── email_service.py            # Email handling ✓
│   └── cloudinary_service.py       # File uploads ✓
└── routes/                         # API endpoints (Blueprints)
    ├── __init__.py                 # ✓
    ├── health.py                   # Health checks ✓
    ├── auth.py                     # Authentication
    ├── news.py                     # News/Articles
    ├── alumni.py                   # Alumni profiles
    ├── admin.py                    # Admin operations
    ├── events.py                   # Events management
    ├── jobs.py                     # Job postings
    └── reactions.py                # Reactions & bookmarks
```

## Modules Created

### Core Modules
- ✓ `config.py` - Centralized configuration
- ✓ `extensions.py` - Flask extensions (CORS, JWT, Cache, etc.)
- ✓ `database.py` - MongoDB connection and indexes

### Utils Package
- ✓ `utils/helpers.py` - serialize_doc, enrich_article_submitter, generate_otp
- ✓ `utils/decorators.py` - admin_required, alumni_required
- ✓ `utils/notifications.py` - Mention notifications

### Services Package
- ✓ `services/email_service.py` - Brevo/Gmail email sending
- ✓ `services/cloudinary_service.py` - File upload handling

### Routes Package (Blueprints)
- ✓ `routes/health.py` - Health check and metrics
- TODO: `routes/auth.py` - Register, login, OTP verification
- TODO: `routes/news.py` - News CRUD, categories, tags
- TODO: `routes/alumni.py` - Alumni profiles, directory
- TODO: `routes/admin.py` - Admin operations, user management
- TODO: `routes/events.py` - Events CRUD
- TODO: `routes/jobs.py` - Job postings
- TODO: `routes/reactions.py` - Reactions, bookmarks, views

## Benefits

1. **Maintainability**: Each module has a single responsibility
2. **Testability**: Easier to write unit tests for isolated modules
3. **Scalability**: Easy to add new features without touching existing code
4. **Readability**: Clear structure, easy to navigate
5. **Reusability**: Services and utilities can be reused across routes
6. **Team Collaboration**: Multiple developers can work on different modules

## Migration Strategy

1. ✓ Create core infrastructure (config, extensions, database)
2. ✓ Extract utilities and services
3. Create route blueprints (in progress)
4. Create new app.py with application factory
5. Test each module independently
6. Deploy and verify

## No Logic Changes

All business logic remains identical. This is purely a structural refactoring for better code organization.
