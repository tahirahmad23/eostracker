# EOS Tracker Platform: Business & Research Documentation

## 1. Product Overview (Business Perspective)

The **EOS Tracker Platform** is a specialized SaaS (Software as a Service) solution designed for network infrastructure management. It addresses the critical business need for tracking hardware lifecycle events—specifically End-of-Support (EOS) and End-of-Life (EOL) dates.

### 1.1 Value Proposition
- **Risk Mitigation**: Prevents network downtime and security vulnerabilities by ensuring hardware is replaced or upgraded before support ends.
- **Budget Planning**: Provides transparency into upcoming hardware refresh requirements, allowing for better financial forecasting.
- **Efficiency**: Automates the manual process of tracking vendor announcements and equipment dates.

### 1.2 Business Model & Pricing
The platform operates on a "Freemium" subscription model:
- **Free Tier**: Limited to tracking 3 devices. Ideal for small labs or individual use.
- **Pro Tier ($49/month)**: Unlimited device tracking. Targeted at enterprise network teams.
- **Payment Gateway**: Integrated with **Lemon Squeezy** for global USD payments, handling recurring billing, taxes, and currency conversion.

### 1.3 Key Business Features
- **Device Catalog**: A curated database of network hardware from various vendors.
- **Automated Alerts**: Sequential email notifications sent at 365, 180, 90, and 30-day intervals before a device hits EOS.
- **Customization**: Ability for users to add internal labels (Custom Names) and notes to their tracked infrastructure.
- **Compliance Tracking**: Maintains a history of all alerts sent for audit and compliance purposes.

---

## 2. Technical Architecture (Research Perspective)

The platform is designed with a modular, scalable architecture using modern Python web technologies.

### 2.1 Core Tech Stack
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) - Provides high performance, asynchronous support, and automatic API documentation.
- **Database Logic**: [SQLAlchemy](https://www.sqlalchemy.org/) - Robust ORM for data persistence and relationship management.
- **Template Engine**: [Jinja2](https://palletsprojects.com/p/jinja/) - Server-side rendering for the web dashboard.
- **Task Scheduling**: Automated background worker that runs daily at 09:00 UTC to process alert calculations.
- **Infrastructure**: Fully containerized using **Docker** and **Docker Compose** for consistent deployment across environments.

### 2.2 Data Entity Relationship (Core Models)
- **User**: Core account entity with tier-based permissioning.
- **Device**: Global catalog entry containing vendor-specific EOL/EOS data.
- **TrackedDevice**: Junction entity representing a user's subscription to a specific hardware's lifecycle.
- **Subscription**: Management of payment state and Lemon Squeezy integration.
- **AlertHistory**: Immutable log of sent notifications to ensure reliable delivery and prevent duplication.

### 2.3 Integration Points
- **Lemon Squeezy API**: Subscription lifecycle management and webhook handling for payment events.
- **Email Service**: Asynchronous SMTP/API integration for system notifications.
- **SQLAdmin**: Administrative interface for platform operators to manage users and hardware data.

---

## 3. Operations & Maintenance
- **Logging**: Centralized logging system capturing request flow, access logs, and application errors.
- **Migrations**: [Alembic](https://alembic.sqlalchemy.org/en/latest/) for version-controlled database schema evolutions.
- **Tests**: Automated test suite using [Pytest](https://docs.pytest.org/), covering core services and web routes.

---

## 4. Research Data Insights
Researchers can leverage the platform's database for:
- **Vendor Reliability Analysis**: Tracking which vendors provide longer support lifecycles.
- **Deployment Trends**: Analyzing popular network hardware models across the user base.
- **Lifecycle Forecasting**: Predictive modeling of device obsolescence trends in the industry.
