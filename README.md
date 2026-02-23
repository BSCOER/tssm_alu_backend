# Alumni Portal Backend

This is the backend for the Alumni Portal application, built with Flask and MongoDB. It provides a robust API for managing alumni profiles, news, events, jobs, and user authentication.

## Table of Contents
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [API Documentation](#api-documentation)
- [Deployment](#deployment)

## Features

- **User Authentication**: Secure registration and login with JWT (JSON Web Tokens) and OTP (One-Time Password) verification via Email.
- **Alumni Profiles**: Comprehensive profiles for alumni including education, work experience, skills, and contact information.
- **News & Articles**: Users can submit news articles which undergo an admin approval process. Supports rich text content and image uploads.
- **Events Management**: Create and manage events (reunions, webinars, workshops) with registration tracking.
- **Job Board**: Alumni can post job opportunities for the community.
- **Admin Dashboard**: Specialized endpoints for administrators to manage users, approve/reject content, and view system statistics.
- **Comments**: Commenting system for articles and news.
- **Search & Filtering**: Advanced search capabilities for alumni directory, jobs, and news.
- **Media Management**: Integration with Cloudinary for image hosting.
- **Performance**: Implements caching (Flask-Caching) and rate limiting (Flask-Limiter) for optimization.

## Tech Stack

- **Language**: Python 3.11
- **Framework**: Flask
- **Database**: MongoDB (using PyMongo)
- **Authentication**: Flask-JWT-Extended
- **Caching**: Flask-Caching (Redis ready)
- **Rate Limiting**: Flask-Limiter
- **Image Storage**: Cloudinary
- **Email Service**: Gmail SMTP

## Prerequisites

- Python 3.11 or higher
- MongoDB instance (local or Atlas)
- Cloudinary account
- Gmail account (for SMTP)

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

Create a `.env` file in the root directory with the following variables:

```env
# Flask Security
SECRET_KEY=your_secret_key_here
JWT_SECRET_KEY=your_jwt_secret_key_here

# Database
MONGODB_URI=mongodb+srv://<username>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority

# Email Configuration (Gmail)
GMAIL_EMAIL=your_email@gmail.com
GMAIL_APP_PASSWORD=your_app_password

# Cloudinary Configuration
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret

# Admin Configuration
ADMIN_KEY=your_admin_registration_key
```

## Running the Application

### Development Mode

Run the Flask application directly:

```bash
python app.py
```

The server will start on `http://0.0.0.0:5000`.

### Production Mode (Gunicorn)

Use Gunicorn to run the application in a production environment:

```bash
gunicorn app:app
```

## API Documentation

For detailed information about the API endpoints, request parameters, and responses, please refer to the [API Documentation](API_DOCUMENTATION.md).

## Deployment

The application includes a `runtime.txt` specifying Python 3.11.9, making it compatible with platforms like Heroku. Ensure all environment variables are set in your deployment environment.
