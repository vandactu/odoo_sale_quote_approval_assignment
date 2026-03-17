from odoo import models, fields, api


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    cost = fields.Monetary(
        string="Cost",
        compute="_compute_cost",
        store=True,
        currency_field="currency_id"
    )

    @api.depends("product_id", "product_uom_qty")
    def _compute_cost(self):
        for line in self:
            cost = line.product_id.standard_price or 0.0
            line.cost = cost * line.product_uom_qty
