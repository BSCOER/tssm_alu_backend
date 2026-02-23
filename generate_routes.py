"""
Script to generate modular route blueprints from monolithic app.py
This script extracts routes and creates organized blueprint files
"""
import re
import os

# Read the original app.py
with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Route categories and their patterns
route_categories = {
    'auth': [
        '/auth/register', '/auth/verify-otp', '/auth/resend-otp',
        '/auth/login', '/auth/refresh', '/auth/me', '/auth/logout'
    ],
    'news': [
        '/news', '/categories', '/tags', '/news/mine', '/news/image',
        '/upload/degree-certificate'
    ],
    'alumni': [
        '/alumni/profile', '/alumni/directory', '/alumni/'
    ],
    'admin': [
        '/admin/news', '/admin/users', '/admin/comments', '/admin/settings',
        '/admin/announcements', '/admin/achievements', '/admin/gallery',
        '/admin/startups'
    ],
    'events': ['/events'],
    'jobs': ['/jobs'],
    'reactions': [
        '/articles/<article_id>/reactions', '/articles/<article_id>/bookmark',
        '/articles/<article_id>/view', '/user/bookmarks'
    ]
}

print("Route extraction script")
print("=" * 50)
print("\nThis script helps identify routes to be extracted.")
print("Manual extraction recommended for complex routes.\n")

# Find all routes
route_pattern = r'@app\.route\([\'"]([^\'"]+)[\'"].*?\)\s*(?:@\w+.*?\s*)*def\s+(\w+)'
routes = re.findall(route_pattern, content, re.MULTILINE)

print(f"Found {len(routes)} routes in app.py\n")

# Categorize routes
categorized = {cat: [] for cat in route_categories.keys()}
uncategorized = []

for route_path, func_name in routes:
    categorized_flag = False
    for category, patterns in route_categories.items():
        if any(pattern in route_path for pattern in patterns):
            categorized[category].append((route_path, func_name))
            categorized_flag = True
            break
    if not categorized_flag:
        uncategorized.append((route_path, func_name))

# Print categorization
for category, routes_list in categorized.items():
    if routes_list:
        print(f"\n{category.upper()} Routes ({len(routes_list)}):")
        for route_path, func_name in routes_list:
            print(f"  - {route_path:50} -> {func_name}")

if uncategorized:
    print(f"\nUNCATEGORIZED Routes ({len(uncategorized)}):")
    for route_path, func_name in uncategorized:
        print(f"  - {route_path:50} -> {func_name}")

print("\n" + "=" * 50)
print("Next steps:")
print("1. Review the categorization above")
print("2. Manually extract route functions to blueprint files")
print("3. Update imports and dependencies")
print("4. Test each blueprint independently")
