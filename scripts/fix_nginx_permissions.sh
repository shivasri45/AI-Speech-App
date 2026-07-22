#!/bin/bash
# Add Permissions-Policy header to allow microphone and camera

CONF="/etc/nginx/sites-available/softskills"

# Check if already added
if grep -q "Permissions-Policy" "$CONF"; then
    echo "Permissions-Policy header already present"
else
    # Add before 'gzip on;' line
    sudo sed -i '/gzip on;/i\    add_header Permissions-Policy "microphone=(*), camera=(*), display-capture=(*)";' "$CONF"
    echo "Added Permissions-Policy header"
fi

# Test and reload
sudo nginx -t && sudo systemctl reload nginx && echo "Nginx reloaded successfully"
