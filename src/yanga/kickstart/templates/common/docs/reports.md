---
orphan: true
---

# Reports

{% for title, files in [
    ("All components", report_data.files("component", "merged")),
    ("All containers", report_data.files("container", "merged")),
    ("Variant", report_data.files("variant", "test") + report_data.files("variant", "coverage")),
    ("Overall", report_data.files("overall")),
] %}
{% if files %}

## {{ title }}

```{toctree}
:maxdepth: 1

{% for file in files %}
{{ file }}
{% endfor %}

```

{% endif %}
{% endfor %}
