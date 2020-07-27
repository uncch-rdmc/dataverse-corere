FROM nginx:latest
#WORKDIR /etc/nginx
COPY ./docker/nginx.conf /etc/nginx
COPY ./corere/static/ /static