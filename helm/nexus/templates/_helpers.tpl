{{- define "nexus.name" -}}
nexus
{{- end -}}

{{- define "nexus.fullname" -}}
{{ include "nexus.name" . }}-api
{{- end -}}
