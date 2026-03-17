from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestSaleQuoteApproval(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.partner = cls.env["res.partner"].create({
            "name": "Test Customer",
        })

        cls.product = cls.env["product.product"].create({
            "name": "Test Product",
            "type": "consu",
            "list_price": 100.0,
            "standard_price": 80.0,
        })

        group_user = cls.env.ref("base.group_user")
        group_sale_user = cls.env.ref("sales_team.group_sale_salesman")
        group_leader = cls.env.ref("sale_quote_approval.group_sales_team_leader")
        group_manager = cls.env.ref("sale_quote_approval.group_sales_manager")
        group_finance = cls.env.ref("sale_quote_approval.group_finance_manager")

        cls.sales_user = cls.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Sales User",
            "login": "sales_user_test",
            "email": "sales_user_test@example.com",
            "groups_id": [(6, 0, [group_user.id, group_sale_user.id])],
        })

        cls.leader_user = cls.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Leader User",
            "login": "leader_user_test",
            "email": "leader_user_test@example.com",
            "groups_id": [(6, 0, [group_user.id, group_sale_user.id, group_leader.id])],
        })

        cls.manager_user = cls.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Manager User",
            "login": "manager_user_test",
            "email": "manager_user_test@example.com",
            "groups_id": [(6, 0, [group_user.id, group_sale_user.id, group_manager.id])],
        })

        cls.finance_user = cls.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Finance User",
            "login": "finance_user_test",
            "email": "finance_user_test@example.com",
            "groups_id": [(6, 0, [group_user.id, group_finance.id])],
        })

    def _create_order(self, price_unit, qty=1.0):
        return self.env["sale.order"].create({
            "partner_id": self.partner.id,
            "user_id": self.sales_user.id,
            "order_line": [
                (0, 0, {
                    "product_id": self.product.id,
                    "name": self.product.name,
                    "product_uom_qty": qty,
                    "price_unit": price_unit,
                })
            ],
        })

    def test_approval_type_full(self):
        order = self._create_order(price_unit=70.0, qty=1.0)
        self.assertEqual(order.total_cost, 80.0)
        self.assertEqual(order.amount_total, 70.0)
        self.assertEqual(order.approval_type, "full")

    def test_approval_type_leader(self):
        order = self._create_order(price_unit=100.0, qty=1.0)
        self.assertEqual(order.total_cost, 80.0)
        self.assertEqual(order.approval_type, "leader")

    def test_approval_type_none(self):
        order = self._create_order(price_unit=130.0, qty=1.0)
        self.assertEqual(order.total_cost, 80.0)
        self.assertEqual(order.approval_type, "none")

    def test_request_approval_locks_order(self):
        order = self._create_order(price_unit=100.0, qty=1.0)

        order.with_user(self.sales_user).action_request_approval()

        self.assertEqual(order.approval_state, "pending_leader")
        self.assertTrue(order.locked)

    def test_leader_flow_approval(self):
        order = self._create_order(price_unit=100.0, qty=1.0)

        order.with_user(self.sales_user).action_request_approval()
        order.with_user(self.leader_user).action_approve_leader()

        self.assertEqual(order.approval_state, "approved")
        self.assertEqual(order.approved_leader_by, self.leader_user)

    def test_full_flow_approval(self):
        order = self._create_order(price_unit=70.0, qty=1.0)

        order.with_user(self.sales_user).action_request_approval()
        self.assertEqual(order.approval_state, "pending_leader")

        order.with_user(self.leader_user).action_approve_leader()
        self.assertEqual(order.approval_state, "pending_manager")

        order.with_user(self.manager_user).action_approve_manager()
        self.assertEqual(order.approval_state, "pending_finance")

        order.with_user(self.finance_user).action_approve_finance()
        self.assertEqual(order.approval_state, "approved")
        self.assertEqual(order.approved_finance_by, self.finance_user)

    def test_reject_resets_to_draft(self):
        order = self._create_order(price_unit=70.0, qty=1.0)

        order.with_user(self.sales_user).action_request_approval()
        order.with_user(self.leader_user).action_reject_approval()

        self.assertEqual(order.approval_state, "draft")
        self.assertFalse(order.locked)
        self.assertFalse(order.approved_leader_by)
        self.assertFalse(order.approved_manager_by)
        self.assertFalse(order.approved_finance_by)

    def test_cannot_confirm_before_approval(self):
        order = self._create_order(price_unit=100.0, qty=1.0)

        with self.assertRaises(UserError):
            order.with_user(self.sales_user).action_confirm()

    def test_cannot_send_before_approval(self):
        order = self._create_order(price_unit=100.0, qty=1.0)

        with self.assertRaises(UserError):
            order.with_user(self.sales_user).action_quotation_send()

    def test_sales_user_cannot_approve_leader_step(self):
        order = self._create_order(price_unit=100.0, qty=1.0)
        order.with_user(self.sales_user).action_request_approval()

        with self.assertRaises(UserError):
            order.with_user(self.sales_user).action_approve_leader()
