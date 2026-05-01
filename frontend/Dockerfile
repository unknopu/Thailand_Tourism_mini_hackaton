FROM nginx:alpine

# Remove the default nginx config and replace with ours
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/app.conf

# Copy static files (overridden by the volume mount in docker-compose for development)
COPY . /usr/share/nginx/html

EXPOSE 8000

CMD ["nginx", "-g", "daemon off;"]
