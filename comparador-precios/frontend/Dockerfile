# --- Stage 1: Build Stage ---
# Use a specific Node version known to work with Vite/dependencies
FROM node:18-alpine as builder

# Set working directory
WORKDIR /app

# Copy package.json and lock file (or yarn.lock)
COPY package.json package-lock.json* ./
# If using yarn:
# COPY package.json yarn.lock ./

# Install dependencies
RUN npm install
# If using yarn:
# RUN yarn install --frozen-lockfile

# Copy the rest of the application code
COPY . .

# Set the build-time environment variable for the API URL
# This will be baked into the static files.
# It should point to the backend service *as accessible from the browser*.
# For production, this might be the public URL of your backend or load balancer.
# For Docker Compose deployment on a single VM, it might still be relative to the host.
# We'll use a placeholder here, which can be overridden during the build or runtime via Nginx.
ARG VITE_API_BASE_URL=/api/v1 # Default to relative path for proxying
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

# Build the React application for production
RUN npm run build

# --- Stage 2: Production Stage ---
# Use a lightweight Nginx image to serve the static files
FROM nginx:1.25-alpine

# Remove default Nginx configuration
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom Nginx configuration (we'll create this next)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy the built static files from the builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose port 80 for Nginx
EXPOSE 80

# Command to run Nginx in the foreground
CMD ["nginx", "-g", "daemon off;"]
