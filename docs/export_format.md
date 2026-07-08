# Account Export Format

## Overview

The account export provides a complete dump of a user's data including their profile, collections, book statuses, reviews, reading sessions, and friends list. This export is GDPR-friendly and versioned for forward compatibility.

## Endpoint

```
GET /me/export/all.json
```

Requires authentication.

## Version

- `export_version`: 1 (versioned for forward compatibility)

## Response Structure

```json
{
  "export_version": 1,
  "user": {
    "id": "uuid",
    "email": "string",
    "username": "string",
    "display_name": "string",
    "bio": "string or null",
    "avatar_url": "string or null",
    "locale": "string",
    "timezone": "string",
    "is_active": "boolean",
    "is_admin": "boolean"
  },
  "collections": [
    {
      "id": "uuid",
      "name": "string",
      "description": "string or null",
      "is_public": "boolean",
      "cover_image_url": "string or null",
      "sort_order": "integer",
      "created_at": "ISO datetime",
      "updated_at": "ISO datetime"
    }
  ],
  "statuses": [
    {
      "id": "uuid",
      "book_id": "uuid or null",
      "release_id": "uuid or null",
      "status": "want_to_read|reading|read|did_not_finish",
      "acquired_at": "ISO datetime or null",
      "notes": "string or null",
      "lent_to_user_id": "uuid or null",
      "lent_to_name": "string or null",
      "lent_at": "ISO datetime or null",
      "returned_at": "ISO datetime or null",
      "created_at": "ISO datetime",
      "updated_at": "ISO datetime"
    }
  ],
  "reviews": [
    {
      "id": "uuid",
      "book_id": "uuid or null",
      "release_id": "uuid or null",
      "rating": "integer (1-5) or null",
      "title": "string or null",
      "body": "string or null",
      "is_public": "boolean",
      "contains_spoilers": "boolean",
      "created_at": "ISO datetime",
      "updated_at": "ISO datetime"
    }
  ],
  "reading_sessions": [
    {
      "id": "uuid",
      "release_id": "uuid",
      "started_at": "ISO datetime",
      "ended_at": "ISO datetime or null",
      "pages_read": "integer or null",
      "position_start": "integer or null",
      "position_end": "integer or null",
      "position_unit": "page|percent|location|timestamp or null",
      "notes": "string or null",
      "created_at": "ISO datetime",
      "updated_at": "ISO datetime"
    }
  ],
  "friends": [
    {
      "user_id": "uuid",
      "username": "string",
      "display_name": "string",
      "avatar_url": "string or null",
      "since": "ISO datetime"
    }
  ]
}
```

## Fields

### User

- `id`: Unique identifier
- `email`: User's email address
- `username`: Unique username
- `display_name`: User's display name
- `bio`: User's bio (optional)
- `avatar_url`: URL to user's avatar (optional)
- `locale`: User's locale preference
- `timezone`: User's timezone
- `is_active`: Whether account is active
- `is_admin`: Whether user is an admin

### Collections

- `id`: Unique identifier
- `name`: Collection name
- `description`: Collection description (optional)
- `is_public`: Whether collection is publicly visible
- `cover_image_url`: URL to collection cover image (optional)
- `sort_order`: Sort order among user's collections
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp

### Statuses (Book Library)

- `id`: Unique identifier
- `book_id`: ID of the book (optional if release_id is set)
- `release_id`: ID of the release (optional if book_id is set)
- `status`: Reading status (want_to_read, reading, read, did_not_finish)
- `acquired_at`: When the book was acquired (optional)
- `notes`: User's notes about the book (optional)
- `lent_to_user_id`: ID of friend the book was lent to (optional)
- `lent_to_name`: Name of non-friend the book was lent to (optional)
- `lent_at`: When the book was lent (optional)
- `returned_at`: When the book was returned (optional)
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp

### Reviews

- `id`: Unique identifier
- `book_id`: ID of the book reviewed (optional if release_id is set)
- `release_id`: ID of the release reviewed (optional if book_id is set)
- `rating`: Rating (1-5, optional)
- `title`: Review title (optional)
- `body`: Review text (optional)
- `is_public`: Whether review is publicly visible
- `contains_spoilers`: Whether review contains spoilers
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp

### Reading Sessions

- `id`: Unique identifier
- `release_id`: ID of the release being read
- `started_at`: When reading started
- `ended_at`: When reading ended (optional)
- `pages_read`: Number of pages read (optional)
- `position_start`: Starting position (optional)
- `position_end`: Ending position (optional)
- `position_unit`: Unit of position measurement (optional)
- `notes`: Notes about the session (optional)
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp

### Friends

- `user_id`: Friend's user ID
- `username`: Friend's username
- `display_name`: Friend's display name
- `avatar_url`: Friend's avatar URL (optional)
- `since`: When friendship was established

## Example Response

```json
{
  "export_version": 1,
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "username": "johndoe",
    "display_name": "John Doe",
    "bio": "Book lover",
    "avatar_url": "https://example.com/avatar.jpg",
    "locale": "en_US",
    "timezone": "America/New_York",
    "is_active": true,
    "is_admin": false
  },
  "collections": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "name": "Favorites",
      "description": "My favorite books",
      "is_public": true,
      "cover_image_url": null,
      "sort_order": 0,
      "created_at": "2024-01-15T10:00:00Z",
      "updated_at": "2024-01-20T15:30:00Z"
    }
  ],
  "statuses": [],
  "reviews": [],
  "reading_sessions": [],
  "friends": []
}
```
