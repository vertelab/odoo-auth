# Odoo Basic Authentication Module

A lightweight module that adds HTTP Basic Authentication to Odoo, protecting specific domains with browser-based username/password prompts.

## Features

- 🔐 **HTTP Basic Authentication** - Uses browser's native login dialog
- 🌐 **Domain-specific protection** - Configure which domains require authentication
- 🔄 **Wildcard support** - Use `*.domain.com` to protect all subdomains
- ⚡ **Seamless integration** - Works with existing Odoo user accounts

## Installation

1. Place the `auth_from_basic_http` module in your Odoo addons directory

2. Add to your Odoo configuration file:
   ```
   server_wide_modules = base,web,auth_from_basic_http
   basic_auth_domains = your-domain.com, *.staging.com
   ```
   
3. Restart Odoo

## How It Works

When a user visits a protected domain, they'll see a browser login dialog. Authentication uses your existing Odoo user accounts. Once authenticated, users have full access to Odoo.

Perfect for protecting staging servers, development environments, and internal instances.
