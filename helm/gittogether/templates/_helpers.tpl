{{/* Base name for every resource: the release name, or "<release>-gittogether" if it doesn't contain the chart name. */}}
{{- define "gittogether.fullname" -}}
{{- if contains .Chart.Name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{/* Labels on every resource. */}}
{{- define "gittogether.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version }}
{{- end -}}

{{/* Selector labels for one component; call with (dict "ctx" . "component" "backend"). */}}
{{- define "gittogether.selectorLabels" -}}
app.kubernetes.io/name: {{ .ctx.Chart.Name }}
app.kubernetes.io/instance: {{ .ctx.Release.Name }}
app.kubernetes.io/component: {{ .component }}
{{- end -}}

{{- define "gittogether.secretName" -}}
{{- .Values.secrets.existingSecret | default (printf "%s-secrets" (include "gittogether.fullname" .)) -}}
{{- end -}}

{{- define "gittogether.postgresHost" -}}
{{- printf "%s-postgres" (include "gittogether.fullname" .) -}}
{{- end -}}

{{/* Container hardening shared by every container (required by the "restricted" Pod Security level). */}}
{{- define "gittogether.containerSecurityContext" -}}
allowPrivilegeEscalation: false
readOnlyRootFilesystem: true
runAsNonRoot: true
capabilities:
  drop: ["ALL"]
seccompProfile:
  type: RuntimeDefault
{{- end -}}

{{/* Environment shared by the backend's migrate init container and the API container. */}}
{{- define "gittogether.backendEnv" -}}
{{- $secret := include "gittogether.secretName" . -}}
- name: POSTGRES_PASSWORD
  valueFrom:
    secretKeyRef: { name: {{ $secret }}, key: POSTGRES_PASSWORD }
- name: DATABASE_URL
  # $(POSTGRES_PASSWORD) is expanded by Kubernetes from the variable above.
  value: "postgresql+psycopg://{{ .Values.postgres.username }}:$(POSTGRES_PASSWORD)@{{ include "gittogether.postgresHost" . }}:5432/{{ .Values.postgres.database }}"
- name: JWT_SECRET
  valueFrom:
    secretKeyRef: { name: {{ $secret }}, key: JWT_SECRET }
- name: COOKIE_SECURE
  value: {{ .Values.backend.cookieSecure | quote }}
{{- end -}}
