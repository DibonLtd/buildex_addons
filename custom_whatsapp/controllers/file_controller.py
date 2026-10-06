# -*- coding: utf-8 -*-
import logging
import os
import mimetypes
import time
from odoo import http
from odoo.http import request, Response
from odoo.tools import config

_logger = logging.getLogger(__name__)

class WhatsAppFileController(http.Controller):
    
    @http.route('/whatsapp_public_docs/<path:filename>', type='http', auth='public')
    def serve_whatsapp_document(self, filename, **kwargs):
        """Serve files from the WhatsApp public documents directory.
        
        This controller makes files accessible via URL after they've been saved
        by the _save_attachment_to_public method.
        """
        start_time = time.time()
        _logger.info('[File Serve] Request received for file: %s, kwargs: %s', filename, kwargs)
        _logger.info('[File Serve] Request headers: %s', dict(request.httprequest.headers))
        
        try:
            # Get the data directory from Odoo config
            base_dir = config.get('data_dir')
            if not base_dir:
                _logger.error('[File Serve] No data_dir configured in Odoo config')
                return Response(status=404, response="No data directory configured")
                
            # Construct the full file path
            public_dir = os.path.join(base_dir, 'whatsapp_public_docs')
            file_path = os.path.join(public_dir, filename)
            _logger.info('[File Serve] Looking for file at path: %s', file_path)
            
            # Check if directory exists
            if not os.path.isdir(public_dir):
                _logger.error('[File Serve] Public directory does not exist: %s', public_dir)
                # Try to create it
                try:
                    os.makedirs(public_dir, exist_ok=True)
                    _logger.info('[File Serve] Created public directory: %s', public_dir)
                except Exception as e:
                    _logger.error('[File Serve] Failed to create public directory: %s', str(e))
                return Response(status=404, response="Public directory not found")
            
            # Security check - ensure the file is within the public directory
            real_path = os.path.realpath(file_path)
            if not real_path.startswith(os.path.realpath(public_dir)):
                _logger.error('[File Serve] Attempted path traversal: %s', filename)
                return Response(status=403, response="Access denied")
            
            # Check if file exists
            if not os.path.isfile(file_path):
                _logger.error('[File Serve] File not found: %s', file_path)
                # List directory contents to help debugging
                try:
                    dir_contents = os.listdir(public_dir)
                    _logger.info('[File Serve] Directory contents of %s: %s', public_dir, dir_contents)
                except Exception as e:
                    _logger.error('[File Serve] Failed to list directory contents: %s', str(e))
                return Response(status=404, response="File not found")
                
            # Get file stats
            file_stats = os.stat(file_path)
            _logger.info('[File Serve] File stats: size=%d bytes, created=%s', 
                         file_stats.st_size, time.ctime(file_stats.st_ctime))
                
            # Determine content type
            content_type, _ = mimetypes.guess_type(filename)
            if not content_type:
                content_type = 'application/octet-stream'
            _logger.info('[File Serve] Determined content type: %s', content_type)
                
            # Read file and serve
            with open(file_path, 'rb') as f:
                file_content = f.read()
                
            _logger.info('[File Serve] Successfully read file: %s (%s, %d bytes)', 
                         filename, content_type, len(file_content))
                
            # Create response with appropriate headers
            response = Response(
                file_content,
                mimetype=content_type
            )
            response.headers['Content-Disposition'] = f'inline; filename="{filename}"'
            response.headers['Cache-Control'] = 'public, max-age=86400'  # Cache for 24 hours
            response.headers['X-Content-Type-Options'] = 'nosniff'
            
            elapsed_time = time.time() - start_time
            _logger.info('[File Serve] Completed serving file %s in %.3f seconds', filename, elapsed_time)
            return response
            
        except Exception as e:
            _logger.exception('[File Serve] Error serving file %s: %s', filename, str(e))
            return Response(status=500, response="Internal server error")