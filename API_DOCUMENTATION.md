# API Documentation

## Latest Updates (Feb 2026)

- Email auth flows (`/auth/register`, `/auth/verify-otp`, `/auth/resend-otp`, `/auth/forgot-password`, `/auth/reset-password`) are exempt from API rate limiting.
- Added **Alumni Gallery** APIs with year-wise pagination and admin CRUD.
- Added **Student Startups** APIs with pagination/filtering and admin CRUD.
- Achievements now support additional category values including `hackathon`.

## Base URL
All API endpoints are prefixed with `/api/v1`.

## Authentication
Most endpoints require authentication using a JSON Web Token (JWT).
Include the token in the `Authorization` header:
```
Authorization: Bearer <your_access_token>
```

## Endpoints

### 1. Authentication

#### Register
- **URL**: `/auth/register`
- **Method**: `POST`
- **Description**: Register a new user.
- **Body**:
  ```json
  {
    "username": "user123",
    "email": "user@example.com",
    "password": "password123",
    "admin_key": "optional_admin_key"
  }
  ```
- **Response**: `201 Created`

#### Verify OTP
- **URL**: `/auth/verify-otp`
- **Method**: `POST`
- **Description**: Verify email and complete registration.
- **Body**:
  ```json
  {
    "email": "user@example.com",
    "otp": "123456"
  }
  ```
- **Response**: `201 Created` (Returns tokens)

#### Resend OTP
- **URL**: `/auth/resend-otp`
- **Method**: `POST`
- **Description**: Resend OTP for email verification.
- **Body**:
  ```json
  {
    "email": "user@example.com"
  }
  ```
- **Response**: `200 OK`

#### Login
- **URL**: `/auth/login`
- **Method**: `POST`
- **Description**: Authenticate user and get tokens.
- **Body**:
  ```json
  {
    "email": "user@example.com",
    "password": "password123"
  }
  ```
- **Response**: `200 OK`
  ```json
  {
    "message": "Login successful",
    "access_token": "...",
    "refresh_token": "...",
    "user": { ... }
  }
  ```

#### Refresh Token
- **URL**: `/auth/refresh`
- **Method**: `POST`
- **Header**: `Authorization: Bearer <refresh_token>`
- **Description**: Get a new access token.
- **Response**: `200 OK`

#### Get Current User
- **URL**: `/auth/me`
- **Method**: `GET`
- **Header**: `Authorization: Bearer <access_token>`
- **Description**: Get details of the currently logged-in user.
- **Response**: `200 OK`

#### Logout
- **URL**: `/auth/logout`
- **Method**: `POST`
- **Header**: `Authorization: Bearer <access_token>`
- **Description**: Logout user.
- **Response**: `200 OK`

---

### 2. News & Articles

#### List Categories
- **URL**: `/categories`
- **Method**: `GET`
- **Description**: Get a list of all news categories.

#### List Tags
- **URL**: `/tags`
- **Method**: `GET`
- **Description**: Get a list of all used tags.

#### List News
- **URL**: `/news`
- **Method**: `GET`
- **Query Params**:
  - `page`: Page number (default 1)
  - `per_page`: Items per page (default 10)
  - `status`: Filter by status (default 'approved')
  - `category`: Filter by category
  - `tag`: Filter by tag
  - `search`: Search query
- **Description**: Get a list of news articles.

#### Get My News
- **URL**: `/news/mine`
- **Method**: `GET`
- **Header**: `Authorization: Bearer <access_token>`
- **Description**: Get articles submitted by the current user.

#### Get Single News
- **URL**: `/news/<news_id>`
- **Method**: `GET`
- **Description**: Get a specific approved news article.

#### Submit News
- **URL**: `/news`
- **Method**: `POST`
- **Header**: `Authorization: Bearer <access_token>`
- **Body**:
  ```json
  {
    "title": "News Title",
    "content": "News Content (Markdown supported)",
    "summary": "Short summary",
    "category": "Technology",
    "tags": ["tech", "ai"],
    "image_url": "http://image.url"
  }
  ```
- **Response**: `201 Created`

#### Update News
- **URL**: `/news/<news_id>`
- **Method**: `PUT`
- **Header**: `Authorization: Bearer <access_token>`
- **Description**: Update a news article (Author or Admin only).

#### Delete News
- **URL**: `/news/<news_id>`
- **Method**: `DELETE`
- **Header**: `Authorization: Bearer <access_token>`
- **Description**: Delete a news article (Author or Admin only).

#### Upload News Image
- **URL**: `/news/image`
- **Method**: `POST`
- **Header**: `Authorization: Bearer <access_token>`
- **Body**: Form-data with `image` file.
- **Description**: Upload an image for a news article.

---

### 3. Alumni Profiles

#### Create Profile
- **URL**: `/alumni/profile`
- **Method**: `POST`
- **Header**: `Authorization: Bearer <access_token>`
- **Body**:
  ```json
  {
    "full_name": "John Doe",
    "graduation_year": 2020,
    "batch": "2016-2020",
    "department": "Computer Science",
    "current_company": "Tech Corp",
    "linkedin_url": "..."
    ...
  }
  ```
- **Response**: `201 Created`

#### Get My Profile
- **URL**: `/alumni/profile`
- **Method**: `GET`
- **Header**: `Authorization: Bearer <access_token>`
- **Description**: Get the current user's alumni profile.

#### Update Profile
- **URL**: `/alumni/profile`
- **Method**: `PUT`
- **Header**: `Authorization: Bearer <access_token>`
- **Description**: Update the current user's alumni profile.

#### Alumni Directory
- **URL**: `/alumni/directory`
- **Method**: `GET`
- **Header**: `Authorization: Bearer <access_token>`
- **Query Params**:
  - `page`, `per_page`
  - `graduation_year`
  - `department`
  - `batch`
  - `company`
  - `search`
- **Description**: Search through alumni profiles.

#### Get Specific Alumni
- **URL**: `/alumni/<alumni_id>`
- **Method**: `GET`
- **Header**: `Authorization: Bearer <access_token>`
- **Description**: Get a specific alumni profile by ID.

---

### 4. Events

#### List Events
- **URL**: `/events`
- **Method**: `GET`
- **Query Params**:
  - `page`, `per_page`
  - `type`: Filter by event type
  - `upcoming`: `true` (default) or `false`
- **Description**: Get a list of events.

#### Create Event
- **URL**: `/events`
- **Method**: `POST`
- **Header**: `Authorization: Bearer <access_token>`
- **Description**: Create a new event (Alumni only).

#### Register for Event
- **URL**: `/events/<event_id>/register`
- **Method**: `POST`
- **Header**: `Authorization: Bearer <access_token>`
- **Description**: Register the current user for an event.

---

### 5. Jobs

#### List Jobs
- **URL**: `/jobs`
- **Method**: `GET`
- **Query Params**:
  - `page`, `per_page`
  - `job_type`, `location`, `company`
- **Description**: List active job postings.

#### Post Job
- **URL**: `/jobs`
- **Method**: `POST`
- **Header**: `Authorization: Bearer <access_token>`
- **Description**: Post a new job opportunity (Alumni only).

---

### 6. User & Profile

#### Get My User Profile
- **URL**: `/profile`
- **Method**: `GET`
- **Header**: `Authorization: Bearer <access_token>`
- **Description**: Get current user's profile details including articles and alumni info.

#### Update User Profile
- **URL**: `/profile`
- **Method**: `PUT`
- **Header**: `Authorization: Bearer <access_token>`
- **Body**: `{ "bio": "...", "profile_image": "..." }`
- **Description**: Update user details (bio, image).

#### Upload Profile Image
- **URL**: `/profile/image`
- **Method**: `POST`
- **Header**: `Authorization: Bearer <access_token>`
- **Body**: Form-data with `image` file.
- **Description**: Upload and update profile image.

#### Change Password
- **URL**: `/profile/password`
- **Method**: `PUT`
- **Header**: `Authorization: Bearer <access_token>`
- **Body**: `{ "old_password": "...", "new_password": "..." }`
- **Description**: Change user password.

#### Get Public User Profile
- **URL**: `/users/<user_id>`
- **Method**: `GET`
- **Header**: `Authorization: Bearer <access_token>`
- **Description**: Get public profile of any user.

---

### 7. Admin

**Note**: All admin endpoints require `is_admin=True` for the user.

#### Get Pending News
- **URL**: `/admin/news/pending`
- **Method**: `GET`

#### Approve News
- **URL**: `/admin/news/<news_id>/approve`
- **Method**: `POST`

#### Reject News
- **URL**: `/admin/news/<news_id>/reject`
- **Method**: `POST`
- **Body**: `{ "reason": "..." }`

#### Manage Users
- **URL**: `/admin/users`
- **Method**: `GET` (List), `POST` (Create Admin)
- **URL**: `/admin/users/<user_id>`
- **Method**: `DELETE`

#### News Management
- **URL**: `/admin/news`
- **Method**: `GET` (List all)
- **URL**: `/admin/news/history`
- **Method**: `GET` (List approved/rejected history)

#### Comments Management
- **URL**: `/admin/comments`
- **Method**: `GET`
- **URL**: `/admin/comments/<comment_id>`
- **Method**: `DELETE`

#### System Stats
- **URL**: `/admin/stats`
- **Method**: `GET`
- **Description**: Get dashboard statistics.

#### Settings
- **URL**: `/admin/settings`
- **Method**: `GET`, `PUT`
- **Description**: Manage system settings.

---

### 8. System & Health

#### Health Check
- **URL**: `/`
- **Method**: `GET`
- **Response**: Service status.

#### Metrics
- **URL**: `/metrics`
- **Method**: `GET`
- **Header**: `Authorization: Bearer <access_token>` (Admin only)
- **Description**: Get system metrics.

---

### 9. Achievements

#### List Achievements
- **URL**: `/achievements`
- **Method**: `GET`
- **Query Params**:
  - `page`, `limit`
  - `category` (e.g. `academic`, `hackathon`, `sports`, `cultural`, `placement`, `other`)
  - `featured=true|false`

#### Get Achievement
- **URL**: `/achievements/<achievement_id>`
- **Method**: `GET`

#### Create Achievement (Admin)
- **URL**: `/achievements`
- **Method**: `POST`
- **Header**: `Authorization: Bearer <access_token>`
- **Body**: Multipart form-data (`title`, `description`, `category`, optional metadata, required `image`)

#### Update Achievement (Admin)
- **URL**: `/achievements/<achievement_id>`
- **Method**: `PUT`
- **Header**: `Authorization: Bearer <access_token>`

#### Delete Achievement (Admin)
- **URL**: `/achievements/<achievement_id>`
- **Method**: `DELETE`
- **Header**: `Authorization: Bearer <access_token>`

---

### 10. Alumni Gallery

#### List Gallery Items
- **URL**: `/gallery`
- **Method**: `GET`
- **Query Params**:
  - `page`, `limit`
  - `year` (optional)
- **Description**: Public year-wise image listing with pagination for infinite scroll.

#### Create Gallery Item (Admin)
- **URL**: `/gallery`
- **Method**: `POST`
- **Header**: `Authorization: Bearer <access_token>`
- **Body**: Multipart form-data (`title`, `description`, `year`, required `image`)

#### Update Gallery Item (Admin)
- **URL**: `/gallery/<item_id>`
- **Method**: `PUT`
- **Header**: `Authorization: Bearer <access_token>`

#### Delete Gallery Item (Admin)
- **URL**: `/gallery/<item_id>`
- **Method**: `DELETE`
- **Header**: `Authorization: Bearer <access_token>`

---

### 11. Student Startups

#### List Startups
- **URL**: `/startups`
- **Method**: `GET`
- **Query Params**:
  - `page`, `limit`
  - `year` (optional)

#### Create Startup (Admin)
- **URL**: `/startups`
- **Method**: `POST`
- **Header**: `Authorization: Bearer <access_token>`
- **Body**:
  ```json
  {
    "name": "Startup Name",
    "description": "What it does",
    "website_url": "https://example.com",
    "founder_name": "Founder Name",
    "year": 2025,
    "is_featured": true
  }
  ```

#### Update Startup (Admin)
- **URL**: `/startups/<startup_id>`
- **Method**: `PUT`
- **Header**: `Authorization: Bearer <access_token>`

#### Delete Startup (Admin)
- **URL**: `/startups/<startup_id>`
- **Method**: `DELETE`
- **Header**: `Authorization: Bearer <access_token>`
