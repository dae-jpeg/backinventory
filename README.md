# inventory_qrmanagement

A Django backend for a QR-based inventory management system. This project enables real-time access to user or item profiles through QR code scanning, supports JWT authentication, and uses WebSockets for multi-screen updates.

## 🚀 Features

- 🔐 JWT Authentication
- 📷 QR Code scanning and profile access
- 🧠 Real-time screen sync using WebSockets
- 🗃️ PostgreSQL database
- 🌍 **Multi-tenancy with region-based data isolation**
- 📦 Environment variable management with `.env`

## 🏢 Multi-Tenancy Architecture

This backend is designed for multi-tenancy using a **region-based** approach:

- **Region Model**: Each tenant is represented by a `Region` (e.g., different campuses, organizations, or departments).
- **Data Isolation**: Users, items, and transactions are associated with a specific region. Data and permissions are scoped to each region, ensuring isolation between tenants.
- **Super Admins**: Super admin users can access and manage data across all regions, while regular admins and users are restricted to their assigned region.
- **Region Middleware**: Every API request is processed by middleware that determines the current region context (from JWT, headers, query params, or subdomain), ensuring correct data access and isolation.
- **Region Management**: Regions can be created, updated, and assigned to users and items. Unique constraints (such as user ID numbers and item IDs) are enforced per region.

This architecture allows you to serve multiple organizations or locations from a single backend instance, with strong data separation and flexible access control.

## 🛠️ Technologies Used

- Python 3
- Django 5.2.1
- Django REST Framework
- PostgreSQL
- WebSockets (Django Channels)
- JWT via SimpleJWT
- Pillow, QRCode
- Dotenv, Debug Toolbar, Gunicorn, Whitenoise

## 📦 Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/dae-jpeg/inventory_qrmanagement.git
cd inventory_qrmanagement
