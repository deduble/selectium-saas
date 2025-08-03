-- Enable required PostgreSQL extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Insert default subscription plans for billing system functionality
-- These plans are required for the billing endpoints to function properly
INSERT INTO subscription_plans (id, name, price_cents, monthly_compute_units, max_concurrent_tasks, is_active, lemon_squeezy_variant_id) VALUES
('free', 'Free', 0, 100, 1, true, NULL),
('starter', 'Starter', 1900, 1000, 3, true, 'variant_id_starter'),
('professional', 'Professional', 4900, 5000, 10, true, 'variant_id_professional'),
('enterprise', 'Enterprise', 9900, 25000, 50, true, 'variant_id_enterprise')
ON CONFLICT (id) DO UPDATE SET
name = EXCLUDED.name,
price_cents = EXCLUDED.price_cents,
monthly_compute_units = EXCLUDED.monthly_compute_units,
max_concurrent_tasks = EXCLUDED.max_concurrent_tasks,
is_active = EXCLUDED.is_active,
lemon_squeezy_variant_id = EXCLUDED.lemon_squeezy_variant_id;

-- Ensure free plan subscription for existing users without active subscriptions
-- This will be handled by application logic during user login/registration