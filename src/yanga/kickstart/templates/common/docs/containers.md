---
orphan: true
---

# Containers

{% for component in report_data.components | sort(attribute="path") %}
{% set files = report_data.files("container", component.name) %}
{% if files %}

## {{ component.path or component.name }}

```{toctree}
:maxdepth: 1

{% for file in files %}
{{ file }}
{% endfor %}

```

{% endif %}
{% endfor %}
