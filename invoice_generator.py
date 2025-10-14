"""
Invoice Generator for Gurtoy Telegram Bot
Generates professional PDF invoices for completed orders.
"""
from __future__ import annotations

import os
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from decimal import Decimal

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas
import qrcode
from PIL import Image as PILImage

logger = logging.getLogger(__name__)

class InvoiceGenerator:
    """Generate professional PDF invoices for Gurtoy orders."""
    
    def __init__(self, supabase_client):
        """
        Initialize invoice generator.
        
        Args:
            supabase_client: Supabase client instance for database access
        """
        self.supabase = supabase_client
        self.invoice_dir = os.path.join(os.path.dirname(__file__), "invoice", "generated_invoice")
        self.logo_path = os.path.join(os.path.dirname(__file__), "invoice", "GURTOY Registered Trademark Logo.png")
        
        # Ensure invoice directory exists
        os.makedirs(self.invoice_dir, exist_ok=True)
        
        # Company information
        self.company_info = {
            "name": "GURTOY",
            "tagline": "Premium Toy Store",
            "address": "Shop No. 6/7, Char Khamba Road, Model Town",
            "city": "Ludhiana, Punjab - 141001, India",
            "phone": "8300000086",
            "alt_phone": "9056010298",
            "email": "thegurtoy@gmail.com",
            "whatsapp": "8300000086",
            "owner": "Kawardeep Singh Khurana"
        }
    
    async def generate_invoice(self, order_id: str) -> Optional[str]:
        """
        Generate invoice PDF for an order.
        
        Args:
            order_id: Order ID (e.g., GUR202501030001)
            
        Returns:
            Path to generated PDF file, or None if failed
        """
        try:
            logger.info(f"Generating invoice for order {order_id}")
            
            # Fetch order data
            order_data = await self._fetch_order_data(order_id)
            if not order_data:
                logger.error(f"Could not fetch order data for {order_id}")
                return None
            
            # Generate PDF
            pdf_path = await self._create_invoice_pdf(order_data)
            
            logger.info(f"Invoice generated successfully: {pdf_path}")
            return pdf_path
            
        except Exception as e:
            logger.error(f"Error generating invoice for order {order_id}: {e}", exc_info=True)
            return None
    
    async def _fetch_order_data(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch complete order data from database.
        
        Args:
            order_id: Order ID
            
        Returns:
            Dictionary with order, items, and payment data
        """
        try:
            # Use the get_order_details function
            result = self.supabase.rpc("get_order_details", {"p_order_id": order_id}).execute()
            
            if not result.data or len(result.data) == 0:
                logger.error(f"No order found for {order_id}")
                return None
            
            data = result.data[0]
            
            # Parse the JSONB data
            order_info = data.get("order_data", {})
            items_data = data.get("items_data", [])
            payment_data = data.get("payment_data", {})
            
            # Parse shipping address if it's a string
            shipping_address = order_info.get("shipping_address", {})
            if isinstance(shipping_address, str):
                try:
                    shipping_address = json.loads(shipping_address)
                except:
                    shipping_address = {}
            
            return {
                "order_id": order_info.get("order_id"),
                "order_internal_id": order_info.get("id"),
                "status": order_info.get("status"),
                "total_amount": float(order_info.get("total_amount", 0)),
                "currency": order_info.get("currency", "INR"),
                "customer_name": order_info.get("customer_name"),
                "customer_phone": order_info.get("customer_phone"),
                "customer_email": order_info.get("customer_email"),
                "shipping_address": shipping_address,
                "created_at": order_info.get("created_at"),
                "payment_completed_at": order_info.get("payment_completed_at"),
                "items": items_data,
                "payment": payment_data
            }
            
        except Exception as e:
            logger.error(f"Error fetching order data for {order_id}: {e}", exc_info=True)
            return None
    
    async def _create_invoice_pdf(self, order_data: Dict[str, Any]) -> str:
        """
        Create PDF invoice using ReportLab.
        
        Args:
            order_data: Complete order data dictionary
            
        Returns:
            Path to generated PDF file
        """
        order_id = order_data["order_id"]
        pdf_filename = f"Gurtoy_Invoice_{order_id}.pdf"
        pdf_path = os.path.join(self.invoice_dir, pdf_filename)
        
        # Create PDF document
        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=A4,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=0.5*inch,
            bottomMargin=0.5*inch
        )
        
        # Container for PDF elements
        story = []
        
        # Get styles
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#2C3E50'),
            spaceAfter=6,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#7F8C8D'),
            spaceAfter=12,
            alignment=TA_CENTER
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=12,
            textColor=colors.HexColor('#2C3E50'),
            spaceAfter=6,
            spaceBefore=12,
            fontName='Helvetica-Bold'
        )
        
        # Add logo if exists
        if os.path.exists(self.logo_path):
            try:
                logo = Image(self.logo_path, width=3.5*inch, height=1.5*inch)
                logo.hAlign = 'CENTER'
                story.append(logo)
                story.append(Spacer(1, 0.1*inch))
            except Exception as e:
                logger.warning(f"Could not add logo to invoice: {e}")
        
        # Company header
        story.append(Paragraph(self.company_info["name"], title_style))
        story.append(Paragraph(self.company_info["tagline"], subtitle_style))
        story.append(Paragraph(
            f"{self.company_info['address']}<br/>"
            f"{self.company_info['city']}<br/>"
            f"📞 {self.company_info['phone']} | 📧 {self.company_info['email']}",
            subtitle_style
        ))
        
        story.append(Spacer(1, 0.2*inch))
        
        # Invoice title
        invoice_title_style = ParagraphStyle(
            'InvoiceTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#E74C3C'),
            alignment=TA_CENTER,
            spaceAfter=12,
            fontName='Helvetica-Bold'
        )
        story.append(Paragraph("TAX INVOICE", invoice_title_style))
        
        # Invoice details table
        created_date = datetime.fromisoformat(order_data["created_at"].replace('Z', '+00:00')) if order_data.get("created_at") else datetime.now()
        payment_date = datetime.fromisoformat(order_data["payment_completed_at"].replace('Z', '+00:00')) if order_data.get("payment_completed_at") else created_date
        
        invoice_details = [
            ["Invoice No:", order_id, "Date:", created_date.strftime("%d %b %Y")],
            ["Payment Status:", "✅ PAID", "Payment Date:", payment_date.strftime("%d %b %Y")]
        ]
        
        if order_data["payment"].get("razorpay_payment_id"):
            invoice_details.append([
                "Payment ID:", order_data["payment"]["razorpay_payment_id"], "", ""
            ])
        
        details_table = Table(invoice_details, colWidths=[1.5*inch, 2*inch, 1.5*inch, 2*inch])
        details_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2C3E50')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(details_table)
        
        story.append(Spacer(1, 0.3*inch))
        
        # Customer details section
        shipping_addr = order_data.get("shipping_address", {})
        
        customer_data = [
            [Paragraph("<b>BILL TO:</b>", heading_style), Paragraph("<b>SHIP TO:</b>", heading_style)],
            [
                Paragraph(
                    f"{order_data['customer_name']}<br/>"
                    f"📞 {order_data['customer_phone']}<br/>"
                    f"📧 {order_data.get('customer_email', 'N/A')}",
                    styles['Normal']
                ),
                Paragraph(
                    f"{order_data['customer_name']}<br/>"
                    f"{shipping_addr.get('street', 'N/A')}<br/>"
                    f"{shipping_addr.get('city', 'N/A')}, {shipping_addr.get('state', 'N/A')}<br/>"
                    f"PIN: {shipping_addr.get('pincode', 'N/A')}"
                    f"{('<br/>Landmark: ' + shipping_addr.get('landmark')) if shipping_addr.get('landmark') else ''}",
                    styles['Normal']
                )
            ]
        ]
        
        customer_table = Table(customer_data, colWidths=[3.5*inch, 3.5*inch])
        customer_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#BDC3C7')),
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#BDC3C7')),
        ]))
        story.append(customer_table)
        
        story.append(Spacer(1, 0.3*inch))
        
        # Items table
        story.append(Paragraph("ITEM DETAILS", heading_style))
        
        items_data = [["#", "Product Description", "Qty", "Unit Price", "Total"]]
        
        for idx, item in enumerate(order_data["items"], 1):
            # Parse product details
            product_details = item.get("product_details", {})
            if isinstance(product_details, str):
                try:
                    product_details = json.loads(product_details)
                except:
                    product_details = {}
            
            # Build product description
            description_parts = [item["product_title"]]
            if product_details.get("color"):
                description_parts.append(f"Color: {product_details['color']}")
            if product_details.get("age_range"):
                description_parts.append(f"Age: {product_details['age_range']}")
            
            description = "<br/>".join(description_parts)
            
            items_data.append([
                str(idx),
                Paragraph(description, styles['Normal']),
                str(item["quantity"]),
                f"₹{float(item['unit_price']):.2f}",
                f"₹{float(item['total_price']):.2f}"
            ])
        
        # Add subtotal row
        items_data.append([
            "", "", "", 
            Paragraph("<b>SUBTOTAL:</b>", styles['Normal']), 
            Paragraph(f"<b>₹{order_data['total_amount']:.2f}</b>", styles['Normal'])
        ])
        
        # Add total row
        items_data.append([
            "", "", "", 
            Paragraph("<b>TOTAL AMOUNT:</b>", heading_style), 
            Paragraph(f"<b>₹{order_data['total_amount']:.2f}</b>", heading_style)
        ])
        
        items_table = Table(
            items_data, 
            colWidths=[0.5*inch, 3.5*inch, 0.8*inch, 1.3*inch, 1.4*inch]
        )
        items_table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495E')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            
            # Data rows
            ('FONTNAME', (0, 1), (-1, -3), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -3), 9),
            ('ALIGN', (0, 1), (0, -3), 'CENTER'),
            ('ALIGN', (2, 1), (2, -3), 'CENTER'),
            ('ALIGN', (3, 1), (-1, -3), 'RIGHT'),
            ('VALIGN', (0, 1), (-1, -3), 'TOP'),
            
            # Subtotal and total rows
            ('FONTNAME', (3, -2), (-1, -1), 'Helvetica-Bold'),
            ('ALIGN', (3, -2), (-1, -1), 'RIGHT'),
            ('FONTSIZE', (3, -2), (-1, -2), 10),
            ('FONTSIZE', (3, -1), (-1, -1), 12),
            ('TEXTCOLOR', (3, -1), (-1, -1), colors.HexColor('#E74C3C')),
            
            # Grid
            ('GRID', (0, 0), (-1, -3), 0.5, colors.HexColor('#BDC3C7')),
            ('LINEABOVE', (3, -2), (-1, -2), 1, colors.HexColor('#BDC3C7')),
            ('LINEABOVE', (3, -1), (-1, -1), 2, colors.HexColor('#2C3E50')),
            
            # Padding
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(items_table)
        
        story.append(Spacer(1, 0.2*inch))
        
        # Amount in words
        amount_words = self._amount_to_words(order_data['total_amount'])
        story.append(Paragraph(
            f"<b>Amount in Words:</b> {amount_words}",
            styles['Normal']
        ))
        
        story.append(Spacer(1, 0.3*inch))
        
        # Payment details
        if order_data.get("payment"):
            story.append(Paragraph("PAYMENT DETAILS", heading_style))
            
            # Get payment method - try from method field first, then webhook events, then default
            payment_method = order_data["payment"].get("method")
            
            # If method is None, try to extract from webhook events
            if not payment_method:
                webhook_events = order_data["payment"].get("webhook_events", [])
                if webhook_events and len(webhook_events) > 0:
                    # Try to get method from the payment data in webhook
                    try:
                        payment_data = webhook_events[0].get("payload", {}).get("payment", {})
                        payment_method = payment_data.get("method")
                    except:
                        pass
            
            # Default to "Online Payment" if still not found
            if not payment_method:
                payment_method = "Online Payment"
            
            payment_id = order_data["payment"].get("razorpay_payment_id", "N/A")
            
            payment_info = f"""
            <b>Method:</b> {payment_method.upper()}<br/>
            <b>Transaction ID:</b> {payment_id}<br/>
            <b>Status:</b> ✅ Payment Successful
            """
            
            story.append(Paragraph(payment_info, styles['Normal']))
            story.append(Spacer(1, 0.2*inch))
        
        # Terms and conditions
        story.append(Paragraph("TERMS & CONDITIONS", heading_style))
        terms = """
        • 6 months manufacturer warranty on all products<br/>
        • Returns accepted within 7 days with original packaging<br/>
        • For any queries, contact us at 8300000086<br/>
        • Thank you for shopping with Gurtoy! 🎉
        """
        story.append(Paragraph(terms, styles['Normal']))
        
        story.append(Spacer(1, 0.3*inch))
        
        # Footer
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#7F8C8D'),
            alignment=TA_CENTER
        )
        
        story.append(Paragraph(
            "This is a computer-generated invoice. No signature required.<br/>"
            f"For support: {self.company_info['email']} | WhatsApp: {self.company_info['whatsapp']}",
            footer_style
        ))
        
        # Build PDF
        doc.build(story)
        
        return pdf_path
    
    def _amount_to_words(self, amount: float) -> str:
        """
        Convert amount to words (Indian numbering system).
        
        Args:
            amount: Amount in rupees
            
        Returns:
            Amount in words
        """
        try:
            # Simple implementation for common amounts
            units = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"]
            teens = ["Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", 
                     "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
            tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
            
            def convert_below_thousand(n):
                if n == 0:
                    return ""
                elif n < 10:
                    return units[n]
                elif n < 20:
                    return teens[n - 10]
                elif n < 100:
                    return tens[n // 10] + (" " + units[n % 10] if n % 10 != 0 else "")
                else:
                    return units[n // 100] + " Hundred" + (" " + convert_below_thousand(n % 100) if n % 100 != 0 else "")
            
            rupees = int(amount)
            paise = int(round((amount - rupees) * 100))
            
            if rupees == 0:
                result = "Zero Rupees"
            else:
                # Handle crores, lakhs, thousands
                crores = rupees // 10000000
                lakhs = (rupees % 10000000) // 100000
                thousands = (rupees % 100000) // 1000
                hundreds = rupees % 1000
                
                result_parts = []
                
                if crores > 0:
                    result_parts.append(convert_below_thousand(crores) + " Crore")
                if lakhs > 0:
                    result_parts.append(convert_below_thousand(lakhs) + " Lakh")
                if thousands > 0:
                    result_parts.append(convert_below_thousand(thousands) + " Thousand")
                if hundreds > 0:
                    result_parts.append(convert_below_thousand(hundreds))
                
                result = " ".join(result_parts) + " Rupees"
            
            if paise > 0:
                result += " and " + convert_below_thousand(paise) + " Paise"
            
            return result + " Only"
            
        except Exception as e:
            logger.warning(f"Error converting amount to words: {e}")
            return f"Rupees {amount:.2f} Only"