# 01 — Inventario mail.template

**Total:** 76

**Literal From (cualquier @ fijo):** 1

Fuente: `evidence/mail-uat/templates_inventory.json`

## Tabla

| ID | XML ID | Nombre | Modelo | email_from | literal |
|---|---|---|---|---|---|
| 4 | auth_signup.portal_set_password_email | Ajustes: Invitación de nuevo usuario al  | res.users | `{{ (object.company_id.email_formatted or user.email_formatted) }}` | False |
| 5 | auth_totp_mail.mail_template_totp_invite | Ajustes: Invitación para el uso de A2F | res.users | `{{ (object.company_id.email_formatted or user.email_formatted) }}` | False |
| 6 | auth_totp_mail.mail_template_totp_mail_code | Ajustes: Nuevo inicio de sesión A2F | res.users | `{{ (object.company_id.email_formatted or user.email_formatted) }}` | False |
| 3 | auth_signup.mail_template_user_signup_account_created | Ajustes: Nuevo inicio de sesión en el po | res.users | `{{ (object.company_id.email_formatted or user.email_formatted) }}` | False |
| 1 | auth_signup.set_password_email | Ajustes: nueva invitación de usuario | res.users | `{{ (object.company_id.email_formatted or user.email_formatted) }}` | False |
| 2 | auth_signup.mail_template_data_unregistered_users | Ajustes: recordatorio de usuario sin reg | res.users | `{{ (object.company_id.email_formatted or user.email_formatted) }}` | False |
| 78 |  | Alerta: Ticket sin respuesta | helpdesk.ticket | `` | False |
| 84 | sale_amazon.picking_sync_failure | Amazon: error en la sincronización de la | res.users | `{{ (object.company_id.email or object.user_id.email_formatted or user.email_form` | False |
| 83 | sale_amazon.order_sync_failure | Amazon: error en la sincronización de ór | res.users | `{{ (object.company_id.email or object.user_id.email_formatted or user.email_form` | False |
| 85 | sale_amazon.inventory_sync_failure | Amazon: error en la sincronización del i | res.users | `{{ (object.company_id.email or object.user_id.email_formatted or user.email_form` | False |
| 20 | account.email_template_edi_self_billing_invoice | Autofactura: Enviando | account.move | `{{ (object.invoice_user_id.email_formatted or object.company_id.email_formatted ` | False |
| 76 |  | Aviso de cierre de ticket | helpdesk.ticket | `` | False |
| 40 | calendar.calendar_template_meeting_update | Calendario: actualización de evento | calendar.event | `{{ (object.user_id.email_formatted or user.email_formatted or '') }}` | False |
| 41 | calendar.calendar_template_delete_event | Calendario: evento eliminado | calendar.event | `{{ (object.user_id.email_formatted or user.email_formatted or '') }}` | False |
| 38 | calendar.calendar_template_meeting_changedate | Calendario: fecha actualizada | calendar.attendee | `{{ (object.event_id.user_id.email_formatted or user.email_formatted or '') }}` | False |
| 37 | calendar.calendar_template_meeting_invitation | Calendario: invitación a reunión | calendar.attendee | `{{ (object.event_id.user_id.email_formatted or user.email_formatted or '') }}` | False |
| 39 | calendar.calendar_template_meeting_reminder | Calendario: recordatorio | calendar.attendee | `{{ (object.event_id.user_id.email_formatted or user.email_formatted or '') }}` | False |
| 29 | purchase.email_template_edi_purchase_done | Compras: orden de compra | purchase.order | `` | False |
| 30 | purchase.email_template_edi_purchase_reminder | Compras: recordatorio de proveedor | purchase.order | `{{ (object.user_id.email_formatted or user.email_formatted) }}` | False |
| 28 | purchase.email_template_edi_purchase | Compras: solicitud de cotización | purchase.order | `` | False |
| 77 |  | Confirmación de solucion de ticket-Resue | helpdesk.ticket | `` | False |
| 79 |  | Confirmación de solucion de ticket-Resue | helpdesk.ticket | `` | False |
| 7 | base_install_request.mail_template_base_install_request | Correo electrónico: solicitud de instala | base.module.install.request | `{{ object.user_id.email_formatted or user.email_formatted }}` | False |
| 65 | documents.mail_template_document_share | Documento: Compartir documento | res.partner | `` | False |
| 63 | documents.mail_template_document_request | Documento: solicitud de documento | documents.document | `` | False |
| 13 | survey.mail_template_user_input_invite | Encuesta: invitación | survey.user_input | `{{ user.email_formatted }}` | False |
| 14 | survey.mail_template_certification | Encuesta: éxito de la certificación | survey.user_input | `{{ (object.survey_id.create_uid.email_formatted or user.email_formatted or user.` | False |
| 8 | stock.mail_template_data_delivery_confirmation | Envío: enviar por correo electrónico | stock.picking | `` | False |
| 32 | account_reports.email_template_customer_statement | Estado de cuenta del cliente | res.partner | `{{ object._get_followup_responsible().email_formatted }}` | False |
| 61 | event.event_subscription | Evento: confirmación del registro | event.registration | `{{ (object.event_id.organizer_id.email_formatted or object.event_id.company_id.e` | False |
| 60 | event.event_registration_mail_template_badge | Evento: gafete del registro | event.registration | `{{ (object.event_id.organizer_id.email_formatted or object.event_id.company_id.e` | False |
| 62 | event.event_reminder | Evento: recordatorio | event.registration | `{{ (object.event_id.organizer_id.email_formatted or object.event_id.company_id.e` | False |
| 17 | account.email_template_edi_invoice | Factura: Envío | account.move | `{{ (object.invoice_user_id.email_formatted or object.company_id.email_formatted ` | False |
| 47 | timesheet_grid.mail_template_timesheet_reminder | Hojas de horas: Recordatorio de aprobado | hr.employee | `{{ (object.user_id.company_id.partner_id.email_formatted or user.email_formatted` | False |
| 46 | timesheet_grid.mail_template_timesheet_reminder_user | Hojas de horas: Recordatorio de empleado | hr.employee | `{{ (object.user_id.company_id.partner_id.email_formatted or user.email_formatted` | False |
| 89 | justech_managed_services.mail_template_assessment_invite | Levantamiento Servicios Administrados —  | justech.managed.service.assessment | `{{ (object.consultant_id.email_formatted or user.email_formatted) }}` | False |
| 9 | gamification.email_template_badge_received | Ludificación: insignia recibida | gamification.badge.user | `` | False |
| 10 | gamification.email_template_goal_reminder | Ludificación: recordatorio para actualiz | gamification.goal | `` | False |
| 11 | gamification.simple_report_template | Ludificación: reporte de desafío | gamification.challenge | `` | False |
| 12 | gamification.mail_template_data_new_rank_reached | Ludificación: se alcanzó un nuevo rango | res.users | `` | False |
| 21 | account.email_template_edi_self_billing_credit_note | Nota de crédito de autofactura: Enviando | account.move | `{{ (object.invoice_user_id.email_formatted or object.company_id.email_formatted ` | False |
| 23 | account.mail_template_invoice_subscriber | Notificación de diario | account.move | `{{ object.invoice_user_id.email_formatted or object.company_id.email_formatted o` | False |
| 45 | crm_iap_mine.lead_generation_no_credits | Notificación de generación de leads IAP | iap.account | `iap@odoo.com` | True |
| 22 | account.mail_template_einvoice_notification | Nueva notificación de facturas electróni | account.journal | `{{ object.company_id.email_formatted }}` | False |
| 66 | documents_hr_payroll.mail_template_new_payslip | Nómina: Nuevo documento de recibo de nóm | hr.payslip | `{{ user.email_formatted }}` | False |
| 67 | documents_hr_payroll.mail_template_new_declaration | Nómina: nueva declaración | hr.employee | `{{ user.email_formatted }}` | False |
| 59 | hr_payroll.mail_template_new_payslip | Nómina: nuevo recibo de nómina | hr.payslip | `{{ user.email_formatted }}` | False |
| 19 | account.email_template_edi_credit_note | Nóta de crédito: enviando | account.move | `{{ (object.invoice_user_id.email_formatted or object.company_id.email_formatted ` | False |
| 33 | account_reports.email_template_generic_tax_instructions | Pago de impuestos | account.return | `{{ (user.email_formatted or object.company_id.email_formatted) }}` | False |
| 18 | account.mail_template_data_payment_receipt | Pago: recibo de pago | account.payment | `` | False |
| 52 | planning.email_template_planning_planning | Planeación: nuevo horario | planning.planning | `{{ object.company_id.email_formatted }}` | False |
| 51 | planning.email_template_slot_single | Planeación: nuevo turno | planning.slot | `{{ object.company_id.email_formatted }}` | False |
| 53 | planning.email_template_shift_switch_email | Planeación: turno reasignado | planning.slot | `{{ object.company_id.email_formatted }}` | False |
| 15 | project.mail_template_data_project_task | Proyecto: Confirmación de recepción de s | project.task | `` | False |
| 35 | account_followup.email_template_followup_1 | Recordatorio de pago | res.partner | `{{ object._get_followup_responsible().email_formatted }}` | False |
| 31 | account_online_synchronization.email_template_sync_reminder | Recordatorio de vencimiento de la conexi | account.journal | `{{ object.company_id.email_formatted or user.email_formatted }}` | False |
| 34 | account_reports.email_template_customer_follow_up_report | Reporte de seguimiento | res.partner | `{{ object._get_followup_responsible().email_formatted }}` | False |
| 36 | account_followup.demo_followup_email_template_2 | Segundo recordatorio | res.partner | `{{ object._get_followup_responsible().email_formatted }}` | False |
| 48 | industry_fsm.mail_template_data_intervention_details | Servicio externo: intervención planeada | project.task | `` | False |
| 49 | industry_fsm.mail_template_data_task_report | Servicio externo: reporte de servicio ex | project.task | `` | False |
| 58 | software_reseller.mail_template_48 | Software Reseller: Send license data | project.task | `` | False |
| 64 | documents.mail_template_document_request_reminder | Solicitud de documento: recordatorio | documents.document | `` | False |
| 82 |  | Soporte al cliente: Confirmacion Resuelt | helpdesk.ticket | `{{ (object.company_id.justech_mail_notification_from or object.company_id.email_` | False |
| 74 | helpdesk.rating_ticket_request_email_template | Soporte al cliente: Solicitud de calific | helpdesk.ticket | `{{ (object.company_id.justech_mail_notification_from or object.company_id.email_` | False |
| 73 | helpdesk.solved_ticket_request_email_template | Soporte al cliente: Ticket cerrado | helpdesk.ticket | `{{ (object.company_id.justech_mail_notification_from or object.company_id.email_` | False |
| 72 | helpdesk.new_ticket_request_email_template | Soporte al cliente: Ticket recibido | helpdesk.ticket | `{{ (object.company_id.justech_mail_notification_from or object.company_id.email_` | False |
| 80 |  | Soporte al cliente: Ticket recibido (cop | helpdesk.ticket | `{{ (object.company_id.justech_mail_notification_from or object.company_id.email_` | False |
| 81 |  | Soporte al cliente: Ticket recibido (cop | helpdesk.ticket | `{{ (object.company_id.justech_mail_notification_from or object.company_id.email_` | False |
| 57 | sale_subscription.mail_template_subscription_alert | Suscripción: Alerta predeterminada por c | sale.order | `{{ (object.user_id.email_formatted or user.email_formatted) }}` | False |
| 54 | sale_subscription.email_payment_close | Suscripción: Error de pago | sale.order | `{{ (object.user_id.email_formatted or object.company_id.email or user.email_form` | False |
| 55 | sale_subscription.email_payment_reminder | Suscripción: Recordatorio de pago | sale.order | `{{ (object.user_id.email_formatted or object.company_id.email or user.email_form` | False |
| 56 | sale_subscription.mail_template_subscription_rating | Suscripción: Solicitud de calificación | sale.order | `{{ (object._rating_get_operator().email_formatted or user.email_formatted) }}` | False |
| 25 | sale.email_template_proforma | Ventas: Enviar factura proforma | sale.order | `{{ (object.user_id.email_formatted or object.company_id.email_formatted or user.` | False |
| 26 | sale.mail_template_sale_confirmation | Ventas: confirmación de orden | sale.order | `{{ (object.user_id.email_formatted or object.company_id.email_formatted or user.` | False |
| 24 | sale.email_template_edi_sale | Ventas: enviar cotización | sale.order | `{{ (object.user_id.email_formatted or object.company_id.email_formatted or user.` | False |
| 27 | sale.mail_template_sale_payment_executed | Ventas: pago realizado | sale.order | `{{ (object.user_id.email_formatted or user.email_formatted) }}` | False |
