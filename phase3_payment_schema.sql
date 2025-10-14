-- Phase 3: Payment and Order Management Schema
-- Extends existing Supabase schema with payment functionality

-- Orders table - Main order tracking
CREATE TABLE IF NOT EXISTS orders (
    id BIGSERIAL PRIMARY KEY,
    order_id TEXT UNIQUE NOT NULL,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    razorpay_order_id TEXT UNIQUE,
    status TEXT DEFAULT 'created' CHECK (status IN ('created', 'pending_payment', 'paid', 'processing', 'shipped', 'delivered', 'cancelled', 'refunded')),
    total_amount DECIMAL(10,2) NOT NULL,
    currency TEXT DEFAULT 'INR',
    
    -- Customer details (collected during order)
    customer_name TEXT NOT NULL,
    customer_phone TEXT NOT NULL,
    customer_email TEXT,
    
    -- Shipping address
    shipping_address JSONB NOT NULL, -- {street, city, state, pincode, landmark}
    
    -- Order metadata
    notes TEXT,
    metadata JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    payment_completed_at TIMESTAMP WITH TIME ZONE,
    shipped_at TIMESTAMP WITH TIME ZONE,
    delivered_at TIMESTAMP WITH TIME ZONE
);

-- Order items table - Products in each order
CREATE TABLE IF NOT EXISTS order_items (
    id BIGSERIAL PRIMARY KEY,
    order_id BIGINT REFERENCES orders(id) ON DELETE CASCADE,
    product_id TEXT NOT NULL, -- References products.product_id
    product_title TEXT NOT NULL, -- Store product name at time of order
    quantity INTEGER DEFAULT 1 CHECK (quantity > 0),
    unit_price DECIMAL(10,2) NOT NULL,
    total_price DECIMAL(10,2) NOT NULL,
    
    -- Product details at time of order (for historical accuracy)
    product_details JSONB DEFAULT '{}', -- Store color, specifications, etc.
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Payments table - Payment tracking and QR codes
CREATE TABLE IF NOT EXISTS payments (
    id BIGSERIAL PRIMARY KEY,
    payment_id TEXT UNIQUE NOT NULL,
    order_id BIGINT REFERENCES orders(id) ON DELETE CASCADE,
    
    -- Razorpay details
    razorpay_payment_id TEXT,
    razorpay_qr_code_id TEXT,
    qr_code_url TEXT,
    qr_code_expires_at TIMESTAMP WITH TIME ZONE,
    
    -- Payment details
    status TEXT DEFAULT 'created' CHECK (status IN ('created', 'pending', 'captured', 'failed', 'cancelled', 'refunded')),
    amount DECIMAL(10,2) NOT NULL,
    currency TEXT DEFAULT 'INR',
    method TEXT, -- 'upi', 'card', 'netbanking', etc.
    
    -- Webhook tracking
    webhook_events JSONB DEFAULT '[]',
    last_webhook_at TIMESTAMP WITH TIME ZONE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    captured_at TIMESTAMP WITH TIME ZONE,
    failed_at TIMESTAMP WITH TIME ZONE
);

-- Customer addresses table - For address reuse and validation
CREATE TABLE IF NOT EXISTS customer_addresses (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    
    -- Address details
    full_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT,
    street_address TEXT NOT NULL,
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    pincode TEXT NOT NULL,
    landmark TEXT,
    
    -- Address type and status
    address_type TEXT DEFAULT 'home' CHECK (address_type IN ('home', 'office', 'other')),
    is_default BOOLEAN DEFAULT false,
    is_verified BOOLEAN DEFAULT false,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Order status history - Track status changes
CREATE TABLE IF NOT EXISTS order_status_history (
    id BIGSERIAL PRIMARY KEY,
    order_id BIGINT REFERENCES orders(id) ON DELETE CASCADE,
    previous_status TEXT,
    new_status TEXT NOT NULL,
    changed_by TEXT, -- 'system', 'admin', 'webhook'
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_orders_order_id ON orders(order_id);
CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_razorpay_order_id ON orders(razorpay_order_id);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at);

CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON order_items(product_id);

CREATE INDEX IF NOT EXISTS idx_payments_payment_id ON payments(payment_id);
CREATE INDEX IF NOT EXISTS idx_payments_order_id ON payments(order_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);
CREATE INDEX IF NOT EXISTS idx_payments_razorpay_payment_id ON payments(razorpay_payment_id);
CREATE INDEX IF NOT EXISTS idx_payments_qr_code_expires_at ON payments(qr_code_expires_at);

CREATE INDEX IF NOT EXISTS idx_customer_addresses_user_id ON customer_addresses(user_id);
CREATE INDEX IF NOT EXISTS idx_customer_addresses_pincode ON customer_addresses(pincode);

CREATE INDEX IF NOT EXISTS idx_order_status_history_order_id ON order_status_history(order_id);

-- Functions for order management

-- Function to create a new order
CREATE OR REPLACE FUNCTION create_order(
    p_user_id BIGINT,
    p_customer_name TEXT,
    p_customer_phone TEXT,
    p_customer_email TEXT,
    p_shipping_address JSONB,
    p_total_amount DECIMAL,
    p_notes TEXT DEFAULT NULL
)
RETURNS TABLE (
    order_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_order_id TEXT;
    v_created_at TIMESTAMP WITH TIME ZONE;
BEGIN
    -- Generate unique order ID
    v_order_id := 'GUR' || TO_CHAR(NOW(), 'YYYYMMDD') || LPAD(nextval('orders_id_seq')::TEXT, 6, '0');
    
    -- Insert order
    INSERT INTO orders (
        order_id, user_id, customer_name, customer_phone, customer_email,
        shipping_address, total_amount, notes, status
    ) VALUES (
        v_order_id, p_user_id, p_customer_name, p_customer_phone, p_customer_email,
        p_shipping_address, p_total_amount, p_notes, 'created'
    ) RETURNING orders.created_at INTO v_created_at;
    
    -- Log status change
    INSERT INTO order_status_history (order_id, new_status, changed_by, notes)
    SELECT id, 'created', 'system', 'Order created'
    FROM orders WHERE orders.order_id = v_order_id;
    
    RETURN QUERY SELECT v_order_id, v_created_at;
END;
$$;

-- Function to add items to order
CREATE OR REPLACE FUNCTION add_order_item(
    p_order_id TEXT,
    p_product_id TEXT,
    p_product_title TEXT,
    p_quantity INTEGER,
    p_unit_price DECIMAL,
    p_product_details JSONB DEFAULT '{}'
)
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
DECLARE
    v_order_internal_id BIGINT;
    v_total_price DECIMAL;
BEGIN
    -- Get internal order ID
    SELECT id INTO v_order_internal_id FROM orders WHERE order_id = p_order_id;
    
    IF v_order_internal_id IS NULL THEN
        RETURN FALSE;
    END IF;
    
    -- Calculate total price
    v_total_price := p_quantity * p_unit_price;
    
    -- Insert order item
    INSERT INTO order_items (
        order_id, product_id, product_title, quantity, 
        unit_price, total_price, product_details
    ) VALUES (
        v_order_internal_id, p_product_id, p_product_title, p_quantity,
        p_unit_price, v_total_price, p_product_details
    );
    
    RETURN TRUE;
END;
$$;

-- Function to update order status
CREATE OR REPLACE FUNCTION update_order_status(
    p_order_id TEXT,
    p_new_status TEXT,
    p_changed_by TEXT DEFAULT 'system',
    p_notes TEXT DEFAULT NULL
)
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
DECLARE
    v_order_internal_id BIGINT;
    v_current_status TEXT;
BEGIN
    -- Get current order details
    SELECT id, status INTO v_order_internal_id, v_current_status 
    FROM orders WHERE order_id = p_order_id;
    
    IF v_order_internal_id IS NULL THEN
        RETURN FALSE;
    END IF;
    
    -- Update order status
    UPDATE orders 
    SET status = p_new_status, updated_at = NOW()
    WHERE id = v_order_internal_id;
    
    -- Log status change
    INSERT INTO order_status_history (
        order_id, previous_status, new_status, changed_by, notes
    ) VALUES (
        v_order_internal_id, v_current_status, p_new_status, p_changed_by, p_notes
    );
    
    -- Update specific timestamp fields
    IF p_new_status = 'paid' THEN
        UPDATE orders SET payment_completed_at = NOW() WHERE id = v_order_internal_id;
    ELSIF p_new_status = 'shipped' THEN
        UPDATE orders SET shipped_at = NOW() WHERE id = v_order_internal_id;
    ELSIF p_new_status = 'delivered' THEN
        UPDATE orders SET delivered_at = NOW() WHERE id = v_order_internal_id;
    END IF;
    
    RETURN TRUE;
END;
$$;

-- Function to get order details with items
CREATE OR REPLACE FUNCTION get_order_details(p_order_id TEXT)
RETURNS TABLE (
    order_data JSONB,
    items_data JSONB,
    payment_data JSONB
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        to_jsonb(o.*) as order_data,
        COALESCE(
            (SELECT jsonb_agg(to_jsonb(oi.*))
             FROM order_items oi 
             WHERE oi.order_id = o.id), 
            '[]'::jsonb
        ) as items_data,
        COALESCE(
            (SELECT to_jsonb(p.*)
             FROM payments p 
             WHERE p.order_id = o.id 
             ORDER BY p.created_at DESC 
             LIMIT 1), 
            '{}'::jsonb
        ) as payment_data
    FROM orders o
    WHERE o.order_id = p_order_id;
END;
$$;

-- Function to validate Indian address
CREATE OR REPLACE FUNCTION validate_indian_address(
    p_pincode TEXT,
    p_state TEXT,
    p_city TEXT
)
RETURNS TABLE (
    is_valid BOOLEAN,
    validation_message TEXT
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Basic pincode validation (6 digits)
    IF p_pincode !~ '^[0-9]{6}$' THEN
        RETURN QUERY SELECT FALSE, 'Pincode must be exactly 6 digits';
        RETURN;
    END IF;
    
    -- Basic state validation (not empty, reasonable length)
    IF LENGTH(TRIM(p_state)) < 2 OR LENGTH(TRIM(p_state)) > 50 THEN
        RETURN QUERY SELECT FALSE, 'State name must be between 2 and 50 characters';
        RETURN;
    END IF;
    
    -- Basic city validation
    IF LENGTH(TRIM(p_city)) < 2 OR LENGTH(TRIM(p_city)) > 50 THEN
        RETURN QUERY SELECT FALSE, 'City name must be between 2 and 50 characters';
        RETURN;
    END IF;
    
    -- If all validations pass
    RETURN QUERY SELECT TRUE, 'Address is valid';
END;
$$;

-- Triggers for automatic timestamp updates
CREATE TRIGGER update_orders_updated_at 
BEFORE UPDATE ON orders 
FOR EACH ROW 
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_payments_updated_at 
BEFORE UPDATE ON payments 
FOR EACH ROW 
EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_customer_addresses_updated_at 
BEFORE UPDATE ON customer_addresses 
FOR EACH ROW 
EXECUTE FUNCTION update_updated_at_column();

-- Row Level Security (RLS) policies
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE order_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE customer_addresses ENABLE ROW LEVEL SECURITY;
ALTER TABLE order_status_history ENABLE ROW LEVEL SECURITY;

-- Users can view their own orders
CREATE POLICY "Users can view own orders" ON orders FOR SELECT USING (
    EXISTS (SELECT 1 FROM users WHERE users.id = orders.user_id AND users.telegram_id::text = auth.uid()::text)
);

-- Users can view their own order items
CREATE POLICY "Users can view own order items" ON order_items FOR SELECT USING (
    EXISTS (
        SELECT 1 FROM orders o 
        JOIN users u ON u.id = o.user_id 
        WHERE o.id = order_items.order_id AND u.telegram_id::text = auth.uid()::text
    )
);

-- Users can view their own payments
CREATE POLICY "Users can view own payments" ON payments FOR SELECT USING (
    EXISTS (
        SELECT 1 FROM orders o 
        JOIN users u ON u.id = o.user_id 
        WHERE o.id = payments.order_id AND u.telegram_id::text = auth.uid()::text
    )
);

-- Users can manage their own addresses
CREATE POLICY "Users can manage own addresses" ON customer_addresses FOR ALL USING (
    EXISTS (SELECT 1 FROM users WHERE users.id = customer_addresses.user_id AND users.telegram_id::text = auth.uid()::text)
);

-- Service role can access everything
CREATE POLICY "Service role full access orders" ON orders FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role full access order_items" ON order_items FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role full access payments" ON payments FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role full access addresses" ON customer_addresses FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role full access status_history" ON order_status_history FOR ALL USING (auth.role() = 'service_role');

-- Add comments for documentation
COMMENT ON TABLE orders IS 'Main orders table with customer details and shipping address';
COMMENT ON TABLE order_items IS 'Items in each order with historical product details';
COMMENT ON TABLE payments IS 'Payment tracking with Razorpay QR codes and webhooks';
COMMENT ON TABLE customer_addresses IS 'Reusable customer addresses with validation';
COMMENT ON TABLE order_status_history IS 'Audit trail for order status changes';

COMMENT ON FUNCTION create_order IS 'Create new order with customer details and address';
COMMENT ON FUNCTION add_order_item IS 'Add product item to existing order';
COMMENT ON FUNCTION update_order_status IS 'Update order status with audit trail';
COMMENT ON FUNCTION get_order_details IS 'Get complete order information with items and payment';
COMMENT ON FUNCTION validate_indian_address IS 'Validate Indian address format and pincode';