# Image Gallery Application

A Python Flask-based web application for image gallery management with user authentication, role-based access control, and admin panel.

## Features

### User Features
- **User Registration & Authentication**: Secure user registration and login
- **Image Gallery**: Browse public images from all users
- **Image Upload**: Upload and manage personal images
- **Image Management**: Edit image titles, descriptions, and visibility
- **My Gallery**: View and manage personal uploaded images

### Admin Features
- **Admin Dashboard**: Overview of system statistics
- **User Management**: 
  - View all users
  - Promote/demote users to/from admin
  - Activate/deactivate user accounts
  - Delete users and their images
- **Image Management**:
  - View all images
  - Delete inappropriate content
  - Toggle image visibility (public/private)

### Technical Features
- SQLite database for data persistence
- Password hashing with Werkzeug security
- Flask-Login for session management
- Image optimization with Pillow
- Responsive Bootstrap UI
- Role-based access control (RBAC)
- Environment variable configuration

## Prerequisites

- Python 3.7+
- pip (Python package manager)

## Installation

1. **Clone or extract the project**
   ```bash
   cd image_gallery
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   
   Edit `.env` file to customize settings:
   ```
   FLASK_APP=run.py
   FLASK_ENV=development
   SECRET_KEY=your-secret-key-change-this-in-production
   DATABASE_URL=sqlite:///image_gallery.db
   UPLOAD_FOLDER=app/static/uploads
   MAX_FILE_SIZE=16777216
   DEBUG=True
   ```

## Running the Application

1. **Start the development server**
   ```bash
   python run.py
   ```

2. **Access the application**
   - Open your browser and go to `http://localhost:5000`

## Usage

### First Time Setup

1. **Register a user account**
   - Click "Register" on the login page
   - Enter username, email, and password
   - Submit to create account

2. **Create Admin Account**
   - **Option A: Using Flask Shell (Recommended)**
     ```bash
     python3
     ```
     Then in the Python shell:
     ```python
     >>> from app import create_app, db
     >>> from app.models.user import User
     >>> app = create_app()
     >>> with app.app_context():
     ...     user = User.query.filter_by(username='your_username').first()
     ...     if user:
     ...         user.is_admin = True
     ...         db.session.commit()
     ...         print(f'✅ {user.username} is now an admin!')
     ...     else:
     ...         print('❌ User not found')
     >>> exit()
     ```
   
   - **Option B: Using Management Script**
     Create `manage_admin.py` in project root:
     ```python
     #!/usr/bin/env python3
     from app import create_app, db
     from app.models.user import User
     
     def make_admin(username):
         app = create_app()
         with app.app_context():
             user = User.query.filter_by(username=username).first()
             if user:
                 user.is_admin = True
                 db.session.commit()
                 print(f'✅ {user.username} is now an admin!')
             else:
                 print(f'❌ User {username} not found')
     
     if __name__ == '__main__':
         import sys
         if len(sys.argv) < 2:
             print('Usage: python manage_admin.py <username>')
             sys.exit(1)
         make_admin(sys.argv[1])
     ```
     Then run:
     ```bash
     python manage_admin.py your_username
     ```
   
   - **Option C: Create Admin During Registration (Manual)**
     1. Register user through web interface
     2. Stop the app
     3. Open `image_gallery.db` with SQLite browser
     4. Find the user in `users` table
     5. Set `is_admin` column to `1`
     6. Restart the app

### User Workflow

1. **Login** with your credentials
2. **Browse Gallery** to see public images
3. **Upload Images** in the "Upload" section
4. **Manage Your Images** in "My Images"
5. **View/Edit** individual images

### Admin Workflow

1. **Login** with admin account
2. **Go to Admin Panel** (dropdown menu)
3. **Dashboard**: View system statistics
4. **Manage Users**: Control user roles and account status
5. **Manage Images**: Monitor and remove inappropriate content

## Admin System Overview

### Admin Capabilities

**User Management** (`/admin/users`)
- **View all users** with creation dates and status
- **Promote to Admin**: Grant admin privileges to users
- **Demote from Admin**: Remove admin privileges
- **Activate/Deactivate**: Enable or disable user accounts (prevents login)
- **Delete Users**: Permanently remove users and their images (from local storage or S3)

**Image Management** (`/admin/images`)
- **View all images** from all users
- **Delete Images**: Remove inappropriate or unwanted content
- **Toggle Visibility**: Make images public or private
- **Batch Operations**: Manage multiple images

**Dashboard** (`/admin/dashboard`)
- **Total Users**: Count of all registered users
- **Total Images**: Count of all uploaded images
- **Total Admins**: Count of admin users
- **Active Users**: Count of enabled user accounts

### Admin Security Features

- **Self-Protection**: Admins cannot:
  - Change their own admin status
  - Deactivate their own account
  - Delete their own account
- **Cascade Delete**: Deleting a user also deletes all their images
- **Role-Based Access**: Only `is_admin=True` users can access admin panel

### Admin Access Control

The admin panel is protected by the `@admin_required` decorator:
```python
@admin_required  # Only admins can access these routes
def admin_feature():
    # Admin functionality here
    pass
```

Non-admin users attempting to access admin routes will be redirected with an error message.

## Project Structure

```
image_gallery/
├── app/
│   ├── __init__.py              # App factory and configuration
│   ├── models/
│   │   ├── user.py              # User model
│   │   └── image.py             # Image model
│   ├── routes/
│   │   ├── auth.py              # Authentication routes
│   │   ├── gallery.py           # Gallery routes
│   │   └── admin.py             # Admin routes
│   ├── static/
│   │   ├── uploads/             # Uploaded images
│   │   ├── css/                 # CSS files
│   │   └── js/                  # JavaScript files
│   └── templates/
│       ├── base.html            # Base template
│       ├── auth/                # Authentication templates
│       ├── gallery/             # Gallery templates
│       └── admin/               # Admin templates
├── .env                         # Environment variables
├── requirements.txt             # Python dependencies
└── run.py                       # Application entry point
```

## Database

The application uses SQLite database with two main tables:

### Users Table
- `id`: Primary key
- `username`: Unique username
- `email`: Unique email
- `password_hash`: Hashed password
- `is_admin`: Admin flag
- `is_active`: Account status
- `created_at`: Registration timestamp

### Images Table
- `id`: Primary key
- `filename`: Stored filename
- `original_filename`: Original upload name
- `title`: Image title
- `description`: Image description
- `user_id`: Owner user ID (foreign key)
- `is_public`: Visibility flag
- `created_at`: Upload timestamp
- `updated_at`: Last modified timestamp

## Security Considerations

- Change `SECRET_KEY` in production
- Use HTTPS in production
- Set `DEBUG=False` in production
- Use a production-grade database (PostgreSQL)
- Implement rate limiting
- Add CSRF protection tokens
- Validate file uploads properly

## Supported Image Formats

- JPG/JPEG
- PNG
- GIF
- WebP

Maximum file size: 16MB (configurable in `.env`)

## Configuration

All configuration is managed through the `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `FLASK_APP` | run.py | Flask app entry point |
| `FLASK_ENV` | development | Flask environment |
| `SECRET_KEY` | - | Session secret key |
| `DATABASE_URL` | sqlite:///image_gallery.db | Database connection |
| `UPLOAD_FOLDER` | app/static/uploads | Image storage path |
| `MAX_FILE_SIZE` | 16777216 | Max upload size (bytes) |
| `DEBUG` | True | Debug mode |

## Troubleshooting

### Issue: Database errors on first run
**Solution**: The database is created automatically. If issues persist, delete `image_gallery.db` and restart.

### Issue: Images not uploading
**Solution**: Ensure `app/static/uploads/` directory exists and is writable.

### Issue: Can't login
**Solution**: Ensure database is initialized and user is registered.

## Future Enhancements

- User profiles with bio and avatar
- Image comments and ratings
- Search and filtering
- Image sharing via links
- Email notifications
- Rate limiting
- Two-factor authentication
- Social features (follow, like)

## License

This project is provided as-is for educational purposes.

## Support

For issues or questions, please review the code comments or modify the application as needed.
