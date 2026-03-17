from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.misc import formatLang


class SaleOrder(models.Model):
    _inherit = "sale.order"

    total_cost = fields.Monetary(
        string="Total Cost",
        compute="_compute_total_cost",
        store=True,
        currency_field="currency_id",
    )

    approval_type = fields.Selection([
            ("none", "No Approval"),
            ("leader", "Sales Team Leader"),
            ("full", "Leader -> Manager -> Finance")
        ],
        compute="_compute_approval_type",
        store=True
    )

    approval_state = fields.Selection([
            ("draft", "Draft"),
            ("pending_leader", "Waiting Sales Team Leader"),
            ("pending_manager", "Waiting Sales Manager"),
            ("pending_finance", "Waiting Finance Manager"),
            ("approved", "Approved"),
        ],
        default="draft",
        tracking=True
    )

    approved_leader_by = fields.Many2one("res.users", string="Leader Approved By", readonly=True, tracking=True)
    approved_manager_by = fields.Many2one("res.users", string="Manager Approved By", readonly=True, tracking=True)
    approved_finance_by = fields.Many2one("res.users", string="Finance Approved By", readonly=True, tracking=True)

    @api.depends("order_line.cost")
    def _compute_total_cost(self):
        for order in self:
            order.total_cost = sum(order.order_line.mapped("cost"))

    @api.depends_context('lang')
    @api.depends('order_line.price_subtotal', 'order_line.cost', 'currency_id', 'company_id', 'payment_term_id')
    def _compute_tax_totals(self):
        super()._compute_tax_totals()
        for order in self:
            tax_totals = order.tax_totals or {}
            currency = order.currency_id or order.company_id.currency_id
            total_cost = order.total_cost or 0.0
            tax_totals['total_cost'] = total_cost
            tax_totals['total_cost_formatted'] = formatLang(
                self.env,
                total_cost,
                currency_obj=currency,
            )

            order.tax_totals = tax_totals

    @api.depends('amount_total', 'total_cost')
    def _compute_approval_type(self):
        for order in self:
            if order.amount_total <= order.total_cost:
                order.approval_type = 'full'
            elif order.amount_total <= order.total_cost * 1.5:
                order.approval_type = 'leader'
            else:
                order.approval_type = 'none'

    @api.model
    def _is_leader_user(self, user=None):
        user = user or self.env.user
        return user.has_group("sale_quote_approval.group_sales_team_leader")

    @api.model
    def _is_manager_user(self, user=None):
        user = user or self.env.user
        return user.has_group("sale_quote_approval.group_sales_manager")

    @api.model
    def _is_finance_user(self, user=None):
        user = user or self.env.user
        return user.has_group("sale_quote_approval.group_finance_manager")

    def action_request_approval(self):
        if self.filtered(lambda o: o.state not in ("draft", "sent")):
            raise UserError(_("Only quotation can request approval."))

        if self.filtered(lambda o: o.approval_type == "none"):
            raise UserError(_("This quotation does not require approval."))

        if self.filtered(lambda o: o.approval_state != "draft"):
            raise UserError(_("Approval has already been requested."))

        self.write({
            "approval_state": "pending_leader",
            "locked": True,
            "approved_leader_by": False,
            "approved_manager_by": False,
            "approved_finance_by": False,
        })

    def action_approve_leader(self):
        if self.filtered(lambda o: o.approval_state != "pending_leader"):
            raise UserError(_("This quotation is not waiting for leader approval."))

        if not self._is_leader_user():
            raise UserError(_("Only Sales Team Leader can approve this stage."))

        for order in self:
            val = {
                "approved_leader_by": self.env.user.id,
            }
            if order.approval_type == "leader":
                val["approval_state"] = "approved"
            else:
                val["approval_state"] = "pending_manager"

            order.write(val)

    def action_approve_manager(self):
        if self.filtered(lambda o: o.approval_state != "pending_manager"):
            raise UserError(_("This quotation is not waiting for manager approval."))

        if not self._is_manager_user():
            raise UserError(_("Only Sales Manager can approve this stage."))

        self.write({
            "approved_manager_by": self.env.user.id,
            "approval_state": "pending_finance",
        })

    def action_approve_finance(self):
        if self.filtered(lambda o: o.approval_state != "pending_finance"):
            raise UserError(_("This quotation is not waiting for finance approval."))

        if not self._is_finance_user():
            raise UserError(_("Only Finance Manager can approve this stage."))

        self.write({
            "approved_finance_by": self.env.user.id,
            "approval_state": "approved",
            "locked": True,
        })

    def action_reject_approval(self):
        if self.filtered(lambda o: o.approval_state not in ("pending_leader", "pending_manager", "pending_finance")):
            raise UserError(_("This quotation is not under approval process."))

        is_leader_user, is_manager_user, is_finance_user = self._is_leader_user(), self._is_manager_user(), self._is_finance_user()
        if self.filtered(
            lambda o:
            (o.approval_state == "pending_leader" and not is_leader_user) or
            (o.approval_state == "pending_manager" and not is_manager_user) or
            (o.approval_state == "pending_finance" and not is_finance_user)
        ):
            raise UserError(_("You cannot reject this approval step."))

        self.write({
            "approval_state": "draft",
            "locked": False,
            "approved_leader_by": False,
            "approved_manager_by": False,
            "approved_finance_by": False,
        })

    def _check_can_send_or_confirm(self):
        if self.filtered(lambda o: o.approval_type != "none" and o.approval_state != "approved"):
            raise UserError(_("This quotation must be approved before sending or confirming."))

    def action_quotation_send(self):
        if not self.env.context.get('bypass_check_approval', False):
            self._check_can_send_or_confirm()
        return super().action_quotation_send()

    def action_confirm(self):
        if not self.env.context.get('bypass_check_approval', False):
            self._check_can_send_or_confirm()
        return super().action_confirm()
