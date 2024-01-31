FROM nginx:alpine

RUN rm /etc/nginx/conf.d/*
RUN rm -rf /etc/ssl/*

COPY ./default.conf /etc/nginx/conf.d/
COPY ./ssl /etc/ssl

EXPOSE 80

CMD [ "nginx", "-g", "daemon off;" ]
