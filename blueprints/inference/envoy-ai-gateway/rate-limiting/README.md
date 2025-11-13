# AI Gateway Rate Limiting

This directory contains the configuration for implementing token-based and request-based rate limiting for the multi-model AI Gateway setup.

## Overview

The rate limiting implementation provides:
- **Token-based limits**: Control usage based on input/output/total tokens
- **Request-based limits**: Control number of requests per time period
- **Per-user limits**: Separate rate limit budgets for each user
- **Model-specific limits**: Different limits for different models
- **Redis backend**: Persistent rate limit counters

## Components

### 1. Redis Backend (`redis.yaml`)
Deploys Redis as the backend storage for rate limit counters.

```bash
kubectl apply -f redis.yaml
```

### 2. Rate Limit Configuration (`ai-gateway-rate-limit.yaml`)
Configures the AI Gateway route with token cost tracking and rate limit policies.

**Rate Limits Configured:**
- Input tokens: 50K per hour per user
- Output tokens: 25K per hour per user  
- Total tokens: 75K per hour per user
- Requests: 60 per minute per user
- Expensive model (gpt-oss-20b): 30 per minute per user

### 3. Envoy Gateway Configuration (`envoy-gateway-values-addon.yaml`)
Helm values to enable rate limiting in Envoy Gateway with Redis backend.

### 4. Test Client (`client-with-rate-limit.py`)
Python client to test rate limiting functionality with various scenarios.

## Deployment Steps

### 1. Deploy Redis
```bash
kubectl apply -f redis.yaml
```

### 2. Update Envoy Gateway (if needed)
```bash
helm upgrade -i eg oci://docker.io/envoyproxy/gateway-helm \
  --version v0.0.0-latest \
  --namespace envoy-gateway-system \
  --create-namespace \
  -f envoy-gateway-values-addon.yaml
```

### 3. Apply Rate Limit Configuration
```bash
kubectl apply -f ai-gateway-rate-limit.yaml
```

### 4. Test Rate Limiting
```bash
python3 client-with-rate-limit.py
```

## Usage

### Client Headers Required

All requests must include:
- `x-ai-eg-model`: Model identifier for routing
- `x-user-id`: User identifier for rate limiting

Example:
```bash
curl -X POST http://<gateway-url>/v1/completions \
  -H "Content-Type: application/json" \
  -H "x-ai-eg-model: openai/gpt-oss-20b" \
  -H "x-user-id: user123" \
  -d '{
    "prompt": "Hello world",
    "max_tokens": 50
  }'
```

### Rate Limit Response

When rate limits are exceeded, the gateway returns HTTP 429 with details about the limit.

## Configuration Details

### Token Cost Tracking

The `llmRequestCosts` section in the AIGatewayRoute tracks:
- `llm_input_token`: Input tokens consumed
- `llm_output_token`: Output tokens generated  
- `llm_total_token`: Total tokens (input + output)

### Rate Limit Rules

Each rule in the BackendTrafficPolicy defines:
- **clientSelectors**: How to identify unique clients (by x-user-id header)
- **limit**: Number of tokens/requests allowed per time unit
- **cost**: How to calculate the cost (from metadata for tokens, fixed for requests)

### Per-Model Limits

Different models can have different rate limits by adding model-specific rules with additional header matching.

## Monitoring

Monitor rate limiting through:
- Gateway logs for rate limit decisions
- Redis for rate limit counter values
- Application metrics for 429 responses

## Customization

Adjust rate limits by modifying the `limit.requests` values in `ai-gateway-rate-limit.yaml`:
- Increase for higher usage allowances
- Decrease for stricter limits
- Add new rules for additional models or user tiers
