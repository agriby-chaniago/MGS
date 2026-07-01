FROM rabbitmq:3.12-management-alpine

# Enabling plugins on this image isn't a plain env-var toggle (an earlier
# plan draft assumed `command:`/`environment:` would work — it doesn't);
# the standard approach is baking it into the image like this.
RUN rabbitmq-plugins enable --offline rabbitmq_prometheus
