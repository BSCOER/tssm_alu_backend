# Backend Structure

## 📁 Clean Modular Architecture

```
backend/tssm_alu_backend/
│
├── 📄 Core Files
│   ├── app.py                          # Main application (original monolithic)
│   ├── app_monolithic_backup.py        # Backup of original code
│   ├── config.py                       # Configuration management
│   ├── extensions.py                   # Flask extensions
│   └── database.py                     # MongoDB connection
│
├── 📁 utils/                           # Utility functions
│   ├── __init__.py
│   ├── helpers.py                      # Common utilities
│   ├── decorators.py                   # Auth decorators
│   └── notifications.py                # Notification system
│
├── 📁 services/                        # Business logic
│   ├── __init__.py
│   ├── email_service.py                # Email delivery
│   └── cloudinary_service.py           # File uploads
│
├── 📁 routes/                          # API blueprints
│   ├── __init__.py
│   └── health.py                       # Health checks
│
├── 📁 logs/                            # Application logs
│
├── 📄 Legacy Endpoints (to be migrated)
│   ├── comments_endpoints.py           # Comments API
│   └── reactions_endpoints.py          # Reactions API
│
└── 📄 Configuration
    ├── requirements.txt                # Python dependencies
    ├── runtime.txt                     # Python version
    ├── README.md                       # Documentation
    └── API_DOCUMENTATION.md            # API reference
```

## 🎯 Current Status

### ✅ Completed
- Core infrastructure (config, extensions, database)
- Utility functions and decorators
- Service layer (email, cloudinary)
- Health check routes
- Cleaned up temporary files

### 🔄 Next Steps
1. Extract remaining routes from `app.py` into blueprints
2. Migrate `comments_endpoints.py` to `routes/comments.py`
3. Migrate `reactions_endpoints.py` to `routes/reactions.py`
4. Create new `app.py` with application factory
5. Test all endpoints
6. Deploy

## 📝 Key Files

### Core
- **app.py**: Original monolithic application (4000+ lines)
- **config.py**: All configuration in one place
- **extensions.py**: Flask extensions (CORS, JWT, Cache, etc.)
- **database.py**: MongoDB connection with indexing

### Utils
- **helpers.py**: serialize_doc, enrich_article_submitter, generate_otp
- **decorators.py**: admin_required, alumni_required
- **notifications.py**: Mention notifications

### Services
- **email_service.py**: Brevo/Gmail email sending
- **cloudinary_service.py**: File upload handling

### Routes
- **health.py**: Health checks and metrics

## 🚀 Usage

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Run application
python app.py

# Or with gunicorn (production)
gunicorn app:app --bind 0.0.0.0:5000
```

## 📚 Documentation

- **README.md**: Main documentation
- **API_DOCUMENTATION.md**: Complete API reference
- **STRUCTURE.md**: This file

---

**Status**: Clean and ready for continued development  
**Repository**: https://github.com/BSCOER/tssm_alu_backend
