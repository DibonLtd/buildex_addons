# from odoo import models, fields, _
# from odoo.exceptions import UserError
# import base64
# import io
# import pandas as pd


# class StockQuantUpdateWizard(models.TransientModel):
#     _name = 'stock.quant.update.wizard'
#     _description = 'Stock Quant Excel Update Wizard'

#     file = fields.Binary(string="Upload Excel File", required=True)
#     file_name = fields.Char(string="File Name")

#     def action_update_records(self):

#         if not self.file:
#             raise UserError(_("Please upload an Excel file."))

#         file_data = base64.b64decode(self.file)
#         file_stream = io.BytesIO(file_data)

#         try:
#             df = pd.read_excel(file_stream)
#         except Exception as e:
#             raise UserError(_("Invalid Excel file: %s") % str(e))

#         required_columns = {'product_code', 'location', 'counted_quantity'}
#         if not required_columns.issubset(df.columns):
#             raise UserError(_("Excel must contain: product_code, location, counted_quantity"))

#         updated = 0
#         errors = []

#         for index, row in df.iterrows():

#             product_code = row['product_code']
#             location_name = row['location']
#             counted_qty = row['counted_quantity']

#             # ✅ Skip empty product_code
#             if pd.isna(product_code) or not str(product_code).strip():
#                 errors.append(f"Row {index+1}: product_code is empty")
#                 continue

#             # ✅ Skip empty location
#             if pd.isna(location_name) or not str(location_name).strip():
#                 errors.append(f"Row {index+1}: location is empty")
#                 continue

#             # ✅ Skip NaN quantity
#             if pd.isna(counted_qty):
#                 errors.append(f"Row {index+1}: counted_quantity is empty or invalid")
#                 continue

#             # ✅ Convert quantity safely
#             try:
#                 counted_qty = float(counted_qty)
#             except (TypeError, ValueError):
#                 errors.append(f"Row {index+1}: Invalid counted_quantity ({counted_qty})")
#                 continue

#             product_code = str(product_code).strip()
#             location_name = str(location_name).strip()

#             product = self.env['product.product'].search(
#                 [('default_code', '=', product_code)],
#                 limit=1
#             )

#             location = self.env['stock.location'].search(
#                 [('complete_name', '=', location_name)],
#                 limit=1
#             )

#             if not product:
#                 errors.append(f"Row {index+1}: Product not found ({product_code})")
#                 continue

#             if not location:
#                 errors.append(f"Row {index+1}: Location not found ({location_name})")
#                 continue

#             quant = self.env['stock.quant'].search([
#                 ('product_id', '=', product.id),
#                 ('location_id', '=', location.id)
#             ], limit=1)

#             if not quant:
#                 errors.append(f"Row {index+1}: Quant not found")
#                 continue

#             quant.write({
#                 'inventory_quantity': counted_qty
#             })

#             updated += 1

#         message = f"{updated} quants updated."

#         if errors:
#             message += "\n\nErrors:\n" + "\n".join(errors[:10])

#         return {
#             'type': 'ir.actions.client',
#             'tag': 'display_notification',
#             'params': {
#                 'title': _('Update Result'),
#                 'message': message,
#                 'type': 'success' if updated else 'warning',
#                 'sticky': True,
#             }
#         }
from odoo import models, fields, _
from odoo.exceptions import UserError
import base64
import io
import pandas as pd


class StockQuantUpdateWizard(models.TransientModel):
    _name = 'stock.quant.update.wizard'
    _description = 'Stock Quant Excel Update Wizard'

    file = fields.Binary(string="Upload Excel File", required=True)
    file_name = fields.Char(string="File Name")

    def action_update_records(self):

        if not self.file:
            raise UserError(_("Please upload an Excel file."))

        file_data = base64.b64decode(self.file)
        file_stream = io.BytesIO(file_data)

        try:
            df = pd.read_excel(file_stream)
        except Exception as e:
            raise UserError(_("Invalid Excel file: %s") % str(e))

        required_columns = {'product_code', 'location', 'counted_quantity'}
        if not required_columns.issubset(df.columns):
            raise UserError(_("Excel must contain: product_code, location, counted_quantity"))

        updated = 0
        errors = []

        for index, row in df.iterrows():

            product_code = row['product_code']
            location_name = row['location']
            counted_qty = row['counted_quantity']

            if pd.isna(product_code) or not str(product_code).strip():
                errors.append(f"Row {index+1}: product_code is empty")
                continue

            if pd.isna(location_name) or not str(location_name).strip():
                errors.append(f"Row {index+1}: location is empty")
                continue

            if pd.isna(counted_qty):
                errors.append(f"Row {index+1}: counted_quantity is empty or invalid")
                continue

            try:
                counted_qty = float(counted_qty)
            except (TypeError, ValueError):
                errors.append(f"Row {index+1}: Invalid counted_quantity ({counted_qty})")
                continue

            product_code = str(product_code).strip()
            location_name = str(location_name).strip()

            product = self.env['product.product'].search(
                [('default_code', '=', product_code)],
                limit=1
            )

            if not product:
                errors.append(f"Row {index+1}: Product not found ({product_code})")
                continue

            location = self.env['stock.location'].search(
                [('complete_name', '=', location_name)],
                limit=1
            )

            if not location:
                errors.append(f"Row {index+1}: Location not found ({location_name})")
                continue

            quant = self.env['stock.quant'].search([
                ('product_id', '=', product.id),
                ('location_id', '=', location.id)
            ], limit=1)

            # ✅ CREATE QUANT IF NOT FOUND
            if not quant:
                self.env['stock.quant'].create({
                    'product_id': product.id,
                    'location_id': location.id,
                    'inventory_quantity': counted_qty,
                })
                updated += 1
                continue

            # ✅ UPDATE EXISTING QUANT
            quant.write({
                'inventory_quantity': counted_qty
            })

            updated += 1

        message = f"{updated} quants updated/created."

        if errors:
            message += "\n\nErrors:\n" + "\n".join(errors[:10])

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Update Result'),
                'message': message,
                'type': 'success' if updated else 'warning',
                'sticky': True,
            }
        }
