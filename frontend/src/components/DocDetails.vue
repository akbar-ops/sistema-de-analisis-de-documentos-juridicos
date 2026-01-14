<template>
  <!-- 🔹 Panel lateral integrado en grid -->
  <div class="doc-details-panel" :class="{ 'is-open': isOpen }">
    <!-- Botón toggle flotante -->
    <v-btn
      icon
      class="toggle-btn"
      color="primary"
      size="small"
      elevation="4"
      @click="togglePanel"
    >
      <v-icon>{{ isOpen ? "mdi-chevron-right" : "mdi-chevron-left" }}</v-icon>
    </v-btn>

    <!-- Contenedor del panel -->
    <div v-if="isOpen" class="panel-container">
      <!-- Contenido cuando hay documento -->
      <div v-if="selected" class="drawer-content">
        <!-- Título destacado -->
        <v-card variant="tonal" color="primary" class="mb-3">
          <v-card-text>
            <div class="text-caption text-grey-darken-1 mb-1">DOCUMENTO</div>
            <div class="text-subtitle-2 font-weight-bold">
              {{ selected.title }}
            </div>
          </v-card-text>
        </v-card>

        <!-- Botones de acción - MOVIDOS AQUÍ para estar en todas las tabs -->
        <div class="px-2 mb-3">
          <v-btn
            v-if="selected.file_path"
            block
            size="small"
            variant="tonal"
            color="primary"
            prepend-icon="mdi-eye"
            @click="openPreview"
            class="mb-2"
          >
            Ver documento
          </v-btn>

          <v-btn
            block
            size="small"
            variant="tonal"
            color="secondary"
            prepend-icon="mdi-message"
            @click="handleOpenChat"
          >
            Abrir chat
          </v-btn>
        </div>

        <!-- Tabs para organizar información -->
        <v-tabs
          v-model="activeTab"
          color="primary"
          density="compact"
          class="mb-2"
        >
          <v-tab value="details">
            <v-icon start size="small">mdi-information</v-icon>
            Detalles
          </v-tab>
          <v-tab value="summary">
            <v-icon start size="small">mdi-text</v-icon>
            Resumen
          </v-tab>
          <v-tab value="persons">
            <v-icon start size="small">mdi-account-multiple</v-icon>
            Personas
            <v-badge
              v-if="validPersonsCount > 0"
              :content="validPersonsCount"
              color="error"
              inline
              class="ml-1"
            />
          </v-tab>
          <v-tab value="analyze">
            <v-icon start size="small">mdi-brain</v-icon>
            Analizar
          </v-tab>
          <v-tab value="similar">
            <v-icon start size="small">mdi-file-compare</v-icon>
            Similares
          </v-tab>
          <v-tab value="cluster" v-if="selected.status === 'processed'">
            <v-icon start size="small">mdi-graph</v-icon>
            Cluster
          </v-tab>
          <v-tab value="writing" v-if="selected.status === 'processed'">
            <v-icon start size="small">mdi-pencil-box-outline</v-icon>
            Redacción
          </v-tab>
        </v-tabs>

        <!-- Contenido de tabs -->
        <v-window v-model="activeTab">
          <!-- TAB 1: DETALLES -->
          <v-window-item value="details">
            <v-list density="compact">
              <v-list-item v-if="selected.doc_type?.name">
                <template #prepend>
                  <v-icon size="small" color="primary"
                    >mdi-file-document</v-icon
                  >
                </template>
                <v-list-item-title class="text-caption"
                  >Tipo de Documento</v-list-item-title
                >
                <v-list-item-subtitle>{{
                  selected.doc_type.name
                }}</v-list-item-subtitle>
              </v-list-item>

              <v-list-item v-if="selected.legal_area?.name">
                <template #prepend>
                  <v-icon size="small" color="primary"
                    >mdi-scale-balance</v-icon
                  >
                </template>
                <v-list-item-title class="text-caption"
                  >Área Legal</v-list-item-title
                >
                <v-list-item-subtitle>{{
                  selected.legal_area.name
                }}</v-list-item-subtitle>
              </v-list-item>

              <v-list-item v-if="selected.legal_subject">
                <template #prepend>
                  <v-icon size="small" color="primary">mdi-gavel</v-icon>
                </template>
                <v-list-item-title class="text-caption"
                  >Materia Legal</v-list-item-title
                >
                <v-list-item-subtitle>{{
                  selected.legal_subject
                }}</v-list-item-subtitle>
              </v-list-item>

              <v-list-item v-if="selected.case_number">
                <template #prepend>
                  <v-icon size="small" color="primary">mdi-folder-text</v-icon>
                </template>
                <v-list-item-title class="text-caption"
                  >Nº Expediente</v-list-item-title
                >
                <v-list-item-subtitle>{{
                  selected.case_number
                }}</v-list-item-subtitle>
              </v-list-item>

              <v-list-item v-if="selected.resolution_number">
                <template #prepend>
                  <v-icon size="small" color="primary"
                    >mdi-file-document-outline</v-icon
                  >
                </template>
                <v-list-item-title class="text-caption"
                  >Nº Resolución</v-list-item-title
                >
                <v-list-item-subtitle>{{
                  selected.resolution_number
                }}</v-list-item-subtitle>
              </v-list-item>

              <v-list-item v-if="selected.issue_place">
                <template #prepend>
                  <v-icon size="small" color="primary">mdi-map-marker</v-icon>
                </template>
                <v-list-item-title class="text-caption"
                  >Lugar de Emisión</v-list-item-title
                >
                <v-list-item-subtitle>{{
                  selected.issue_place
                }}</v-list-item-subtitle>
              </v-list-item>

              <v-list-item v-if="selected.document_date">
                <template #prepend>
                  <v-icon size="small" color="primary">mdi-calendar</v-icon>
                </template>
                <v-list-item-title class="text-caption"
                  >Fecha del Documento</v-list-item-title
                >
                <v-list-item-subtitle>{{
                  formatDate(selected.document_date)
                }}</v-list-item-subtitle>
              </v-list-item>

              <v-list-item v-if="selected.pages">
                <template #prepend>
                  <v-icon size="small" color="primary">mdi-file</v-icon>
                </template>
                <v-list-item-title class="text-caption"
                  >Páginas</v-list-item-title
                >
                <v-list-item-subtitle>{{
                  selected.pages
                }}</v-list-item-subtitle>
              </v-list-item>

              <v-list-item v-if="fileSizeMB && fileSizeMB !== '0.0'">
                <template #prepend>
                  <v-icon size="small" color="primary">mdi-file-outline</v-icon>
                </template>
                <v-list-item-title class="text-caption"
                  >Tamaño</v-list-item-title
                >
                <v-list-item-subtitle>{{ fileSizeMB }} MB</v-list-item-subtitle>
              </v-list-item>

              <v-list-item>
                <template #prepend>
                  <v-icon size="small" color="primary"
                    >mdi-clock-outline</v-icon
                  >
                </template>
                <v-list-item-title class="text-caption"
                  >Fecha de Carga</v-list-item-title
                >
                <v-list-item-subtitle>{{ formattedDate }}</v-list-item-subtitle>
              </v-list-item>

              <v-list-item>
                <template #prepend>
                  <v-icon size="small" color="primary">mdi-information</v-icon>
                </template>
                <v-list-item-title class="text-caption"
                  >Estado</v-list-item-title
                >
                <template #append>
                  <v-chip :color="statusColor" size="small" variant="flat">
                    <v-icon start size="x-small">{{ statusIcon }}</v-icon>
                    {{ statusText }}
                  </v-chip>
                </template>
              </v-list-item>
            </v-list>
          </v-window-item>

          <!-- TAB 2: RESUMEN -->
          <v-window-item value="summary">
            <div v-if="selected.summary" class="pa-3">
              <v-alert
                type="info"
                variant="tonal"
                density="compact"
                icon="mdi-information"
                class="mb-3"
              >
                <div class="text-caption">
                  Este es el resumen generado automáticamente. Para el resumen
                  completo y formateado, abre el <strong>chat</strong>.
                </div>
              </v-alert>

              <div class="summary-content">
                <p
                  class="text-body-2"
                  style="line-height: 1.6; white-space: pre-line"
                >
                  {{ selected.summary }}
                </p>
              </div>
            </div>

            <div v-else class="pa-3 text-center">
              <v-icon size="48" color="grey-lighten-1"
                >mdi-text-box-remove</v-icon
              >
              <p class="text-caption text-grey mt-2">
                No hay resumen disponible
              </p>
            </div>
          </v-window-item>

          <!-- TAB 3: PERSONAS -->
          <v-window-item value="persons">
            <div v-if="hasValidPersons" class="pa-3">
              <div class="persons-grid">
                <v-card
                  v-for="(docPerson, idx) in validPersons"
                  :key="idx"
                  class="person-card mb-2"
                  variant="outlined"
                >
                  <v-card-text class="pa-3">
                    <div class="d-flex align-center">
                      <v-avatar
                        size="40"
                        :color="getRoleColor(docPerson.role)"
                        class="me-3"
                      >
                        <v-icon color="white">mdi-account</v-icon>
                      </v-avatar>
                      <div class="flex-grow-1">
                        <div class="text-subtitle-2 font-weight-bold">
                          {{ docPerson.name || docPerson.person?.name }}
                        </div>
                        <v-chip
                          v-if="docPerson.role"
                          size="x-small"
                          :color="getRoleColor(docPerson.role)"
                          variant="flat"
                          class="mt-1"
                        >
                          {{ docPerson.role }}
                        </v-chip>
                      </div>
                    </div>
                  </v-card-text>
                </v-card>
              </div>
            </div>

            <div v-else class="pa-3 text-center">
              <v-icon size="48" color="grey-lighten-1">mdi-account-off</v-icon>
              <p class="text-caption text-grey mt-2">
                No hay personas registradas
              </p>
            </div>
          </v-window-item>

          <!-- TAB 4: ANÁLISIS MODULAR -->
          <v-window-item value="analyze">
            <div class="pa-3">
              <v-alert
                type="info"
                variant="tonal"
                density="compact"
                icon="mdi-information"
                class="mb-3"
              >
                <div class="text-caption">
                  Puedes analizar partes específicas del documento de forma
                  independiente.
                </div>
              </v-alert>

              <!-- Estado de cada análisis -->
              <div class="analysis-options mb-4">
                <v-card
                  variant="outlined"
                  class="mb-2"
                  :class="getAnalysisCardClass('metadata')"
                >
                  <v-card-text class="pa-3">
                    <div class="d-flex align-center justify-space-between">
                      <div class="d-flex align-center flex-grow-1">
                        <v-icon
                          :color="getAnalysisStatusColor('metadata')"
                          class="me-2"
                        >
                          {{ getAnalysisStatusIcon("metadata") }}
                        </v-icon>
                        <div>
                          <div class="text-subtitle-2">Metadatos</div>
                          <div class="text-caption text-medium-emphasis">
                            Tipo, área legal, fecha, lugar, etc.
                          </div>
                        </div>
                      </div>
                      <v-chip
                        :color="getAnalysisStatusColor('metadata')"
                        size="small"
                        variant="flat"
                      >
                        {{ getAnalysisStatusText("metadata") }}
                      </v-chip>
                    </div>
                  </v-card-text>
                </v-card>

                <v-card
                  variant="outlined"
                  class="mb-2"
                  :class="getAnalysisCardClass('title')"
                >
                  <v-card-text class="pa-3">
                    <div class="d-flex align-center justify-space-between">
                      <div class="d-flex align-center flex-grow-1">
                        <v-icon
                          :color="getAnalysisStatusColor('title')"
                          class="me-2"
                        >
                          {{ getAnalysisStatusIcon("title") }}
                        </v-icon>
                        <div>
                          <div class="text-subtitle-2">Título</div>
                          <div class="text-caption text-medium-emphasis">
                            Título específico basado en partes y decisión
                          </div>
                        </div>
                      </div>
                      <v-chip
                        :color="getAnalysisStatusColor('title')"
                        size="small"
                        variant="flat"
                      >
                        {{ getAnalysisStatusText("title") }}
                      </v-chip>
                    </div>
                  </v-card-text>
                </v-card>

                <v-card
                  variant="outlined"
                  class="mb-2"
                  :class="getAnalysisCardClass('summary')"
                >
                  <v-card-text class="pa-3">
                    <div class="d-flex align-center justify-space-between">
                      <div class="d-flex align-center flex-grow-1">
                        <v-icon
                          :color="getAnalysisStatusColor('summary')"
                          class="me-2"
                        >
                          {{ getAnalysisStatusIcon("summary") }}
                        </v-icon>
                        <div>
                          <div class="text-subtitle-2">Resumen</div>
                          <div class="text-caption text-medium-emphasis">
                            Resumen ejecutivo del documento
                          </div>
                        </div>
                      </div>
                      <v-chip
                        :color="getAnalysisStatusColor('summary')"
                        size="small"
                        variant="flat"
                      >
                        {{ getAnalysisStatusText("summary") }}
                      </v-chip>
                    </div>
                  </v-card-text>
                </v-card>

                <v-card
                  variant="outlined"
                  class="mb-2"
                  :class="getAnalysisCardClass('persons')"
                >
                  <v-card-text class="pa-3">
                    <div class="d-flex align-center justify-space-between">
                      <div class="d-flex align-center flex-grow-1">
                        <v-icon
                          :color="getAnalysisStatusColor('persons')"
                          class="me-2"
                        >
                          {{ getAnalysisStatusIcon("persons") }}
                        </v-icon>
                        <div>
                          <div class="text-subtitle-2">Personas</div>
                          <div class="text-caption text-medium-emphasis">
                            Demandantes, demandados, jueces, etc.
                          </div>
                        </div>
                      </div>
                      <v-chip
                        :color="getAnalysisStatusColor('persons')"
                        size="small"
                        variant="flat"
                      >
                        {{ getAnalysisStatusText("persons") }}
                      </v-chip>
                    </div>
                  </v-card-text>
                </v-card>
              </div>

              <!-- Selección de análisis -->
              <div class="mb-3">
                <p class="text-caption font-weight-medium mb-2">
                  Selecciona qué analizar:
                </p>
                <v-checkbox
                  v-model="analysisParts"
                  value="metadata"
                  label="Metadatos"
                  density="compact"
                  hide-details
                  class="mb-1"
                />
                <v-checkbox
                  v-model="analysisParts"
                  value="title"
                  label="Título"
                  density="compact"
                  hide-details
                  class="mb-1"
                />
                <v-checkbox
                  v-model="analysisParts"
                  value="summary"
                  label="Resumen"
                  density="compact"
                  hide-details
                  class="mb-1"
                />
                <v-checkbox
                  v-model="analysisParts"
                  value="persons"
                  label="Personas"
                  density="compact"
                  hide-details
                />
              </div>

              <!-- Botón de análisis -->
              <v-btn
                block
                color="primary"
                :disabled="analysisParts.length === 0 || analyzingDocument"
                :loading="analyzingDocument"
                @click="analyzeDocument"
              >
                <v-icon start>mdi-brain</v-icon>
                Analizar
                {{
                  analysisParts.length > 0 ? `(${analysisParts.length})` : ""
                }}
              </v-btn>

              <!-- Mensaje de progreso -->
              <v-alert
                v-if="analyzingDocument"
                type="info"
                variant="tonal"
                density="compact"
                class="mt-3"
              >
                <v-progress-linear indeterminate color="primary" class="mb-2" />
                Analizando documento...
              </v-alert>

              <!-- Mensaje de éxito -->
              <v-alert
                v-if="analysisSuccess"
                type="success"
                variant="tonal"
                density="compact"
                class="mt-3"
                closable
                @click:close="analysisSuccess = false"
              >
                ¡Análisis completado exitosamente!
              </v-alert>

              <!-- Mensaje de error -->
              <v-alert
                v-if="analysisError"
                type="error"
                variant="tonal"
                density="compact"
                class="mt-3"
                closable
                @click:close="analysisError = null"
              >
                {{ analysisError }}
              </v-alert>
            </div>
          </v-window-item>

          <!-- TAB 5: DOCUMENTOS SIMILARES -->
          <v-window-item value="similar">
            <div v-if="loadingSimilar" class="pa-3 text-center">
              <v-progress-circular indeterminate size="32" color="primary" />
              <p class="text-caption mt-2 text-medium-emphasis">
                Buscando similares...
              </p>
            </div>

            <v-alert
              v-else-if="similarError"
              type="warning"
              variant="tonal"
              density="compact"
              class="ma-3"
            >
              {{ similarError }}
            </v-alert>

            <div v-else-if="similarDocs.length === 0" class="pa-3 text-center">
              <v-icon size="48" color="grey-lighten-1">mdi-file-search</v-icon>
              <p class="text-caption text-grey mt-2">
                No se encontraron documentos similares
              </p>
            </div>

            <div v-else class="similar-docs-container pa-2">
              <v-card
                v-for="(simDoc, idx) in similarDocs"
                :key="idx"
                class="similar-doc-card mb-3"
                variant="outlined"
              >
                <v-card-text class="pa-3">
                  <!-- Similarity Badges -->
                  <div
                    class="d-flex justify-space-between align-start mb-2 flex-wrap gap-2"
                  >
                    <div class="d-flex gap-1 flex-wrap">
                      <!-- Hybrid Score (principal) -->
                      <v-chip
                        v-if="simDoc.hybrid_score"
                        :color="getSimilarityColor(simDoc.hybrid_score)"
                        size="small"
                        variant="flat"
                        class="similarity-chip"
                      >
                        <v-icon start size="x-small">mdi-star</v-icon>
                        {{ Math.round(simDoc.hybrid_score * 100) }}% Score Final
                      </v-chip>

                      <!-- Semantic Score -->
                      <v-chip
                        v-if="simDoc.similarity_score"
                        color="blue-grey"
                        size="small"
                        variant="outlined"
                      >
                        <v-icon start size="x-small">mdi-semantic-web</v-icon>
                        {{ Math.round(simDoc.similarity_score * 100) }}%
                        Semántico
                      </v-chip>

                      <!-- Metadata Boost -->
                      <v-chip
                        v-if="
                          simDoc.metadata_boost && simDoc.metadata_boost > 0
                        "
                        color="success"
                        size="small"
                        variant="tonal"
                      >
                        <v-icon start size="x-small">mdi-plus-circle</v-icon>
                        +{{ Math.round(simDoc.metadata_boost * 100) }}% Boost
                      </v-chip>

                      <!-- Penalties -->
                      <v-chip
                        v-if="simDoc.penalties && simDoc.penalties < 0"
                        color="warning"
                        size="small"
                        variant="tonal"
                      >
                        <v-icon start size="x-small">mdi-minus-circle</v-icon>
                        {{ Math.round(simDoc.penalties * 100) }}% Penalización
                      </v-chip>
                    </div>

                    <v-icon size="small" color="primary"
                      >mdi-open-in-new</v-icon
                    >
                  </div>

                  <!-- Área clickeable para abrir documento -->
                  <div
                    class="clickeable-area pa-2 rounded mb-2"
                    style="
                      cursor: pointer;
                      background: rgba(var(--v-theme-primary), 0.03);
                    "
                    @click="handleSimilarDocClick(simDoc.document_id)"
                  >
                    <!-- Title -->
                    <div
                      class="text-subtitle-2 font-weight-bold mb-2 similar-title"
                    >
                      {{ simDoc.title }}
                    </div>

                    <!-- Metadata -->
                    <div class="d-flex flex-column gap-1">
                      <div
                        v-if="simDoc.legal_area?.name"
                        class="d-flex align-center"
                      >
                        <v-icon size="x-small" color="primary" class="mr-1"
                          >mdi-scale-balance</v-icon
                        >
                        <span class="text-caption text-medium-emphasis">
                          {{ simDoc.legal_area.name }}
                        </span>
                      </div>

                      <div
                        v-if="simDoc.doc_type?.name"
                        class="d-flex align-center"
                      >
                        <v-icon size="x-small" color="primary" class="mr-1"
                          >mdi-file-document</v-icon
                        >
                        <span class="text-caption text-medium-emphasis">
                          {{ simDoc.doc_type.name }}
                        </span>
                      </div>

                      <div
                        v-if="simDoc.document_date"
                        class="d-flex align-center"
                      >
                        <v-icon size="x-small" color="primary" class="mr-1"
                          >mdi-calendar</v-icon
                        >
                        <span class="text-caption text-medium-emphasis">
                          {{ formatDate(simDoc.document_date) }}
                        </span>
                      </div>
                    </div>

                    <!-- Click hint -->
                    <div
                      class="text-caption text-primary mt-2 d-flex align-center"
                    >
                      <v-icon size="x-small" class="mr-1"
                        >mdi-cursor-default-click</v-icon
                      >
                      Click aquí para ver detalles completos
                    </div>
                  </div>

                  <!-- Similarity Summary - Versión simplificada y entendible -->
                  <div
                    v-if="getSimilarityReasons(simDoc).length > 0"
                    class="mb-2 pa-2 rounded"
                    style="background: rgba(33, 150, 243, 0.05)"
                  >
                    <div
                      class="text-caption font-weight-medium text-primary mb-2 d-flex align-center"
                    >
                      <v-icon size="small" class="mr-1"
                        >mdi-check-decagram</v-icon
                      >
                      <span>Similitudes Encontradas:</span>
                    </div>
                    <div class="d-flex flex-column gap-1">
                      <div
                        v-for="(reason, ridx) in getSimilarityReasons(
                          simDoc
                        ).slice(0, 5)"
                        :key="ridx"
                        class="d-flex align-start"
                      >
                        <v-icon size="small" color="success" class="mr-1 mt-0"
                          >mdi-check-circle</v-icon
                        >
                        <span class="text-caption text-grey-darken-3">{{
                          reason
                        }}</span>
                      </div>
                    </div>
                  </div>

                  <!-- Score Details - Expandible con info más clara -->
                  <v-expansion-panels
                    v-if="simDoc.score_breakdown || simDoc.hybrid_score"
                    variant="accordion"
                    class="mt-2"
                    @click.stop
                  >
                    <v-expansion-panel elevation="0">
                      <v-expansion-panel-title
                        class="text-caption pa-2 bg-grey-lighten-4"
                      >
                        <template v-slot:default="{ expanded }">
                          <div class="d-flex align-center">
                            <v-icon size="small" class="mr-1" color="primary">
                              {{
                                expanded ? "mdi-chevron-up" : "mdi-chevron-down"
                              }}
                            </v-icon>
                            <span class="font-weight-medium">
                              {{
                                expanded
                                  ? "Ocultar Análisis Técnico"
                                  : "Ver Análisis Técnico del Score"
                              }}
                            </span>
                          </div>
                        </template>
                      </v-expansion-panel-title>
                      <v-expansion-panel-text class="pa-3">
                        <!-- Explicación para el usuario -->
                        <v-alert
                          density="compact"
                          type="info"
                          variant="tonal"
                          class="mb-3 text-caption"
                        >
                          Este análisis técnico muestra cómo se calculó el score
                          de similitud final.
                        </v-alert>

                        <div class="text-caption">
                          <!-- Score principal -->
                          <div class="mb-3 pa-2 rounded bg-primary-lighten-5">
                            <div
                              class="d-flex justify-space-between align-center"
                            >
                              <div>
                                <v-icon
                                  size="small"
                                  class="mr-1"
                                  color="primary"
                                  >mdi-star-circle</v-icon
                                >
                                <span class="font-weight-bold text-primary"
                                  >Score Final:</span
                                >
                              </div>
                              <v-chip
                                color="primary"
                                size="small"
                                variant="flat"
                              >
                                {{
                                  Math.round(
                                    (simDoc.hybrid_score ||
                                      simDoc.similarity_score ||
                                      0) * 100
                                  )
                                }}%
                              </v-chip>
                            </div>
                          </div>

                          <!-- Desglose de componentes -->
                          <div v-if="simDoc.score_breakdown">
                            <div
                              class="text-caption font-weight-medium mb-2 text-grey-darken-2"
                            >
                              Componentes del Score:
                            </div>
                            <div
                              v-for="(value, key) in simDoc.score_breakdown"
                              :key="key"
                              class="d-flex justify-space-between align-center mb-2 pa-2 rounded"
                              style="
                                background: rgba(var(--v-theme-surface), 0.5);
                              "
                            >
                              <span class="text-medium-emphasis">
                                <v-icon size="x-small" class="mr-1"
                                  >mdi-circle-small</v-icon
                                >
                                {{ formatScoreKey(key) }}:
                              </span>
                              <v-chip
                                size="x-small"
                                variant="flat"
                                :color="getScoreColor(value)"
                              >
                                {{
                                  typeof value === "number"
                                    ? Math.round(value * 100) + "%"
                                    : value
                                }}
                              </v-chip>
                            </div>
                          </div>
                        </div>
                      </v-expansion-panel-text>
                    </v-expansion-panel>
                  </v-expansion-panels>
                </v-card-text>
              </v-card>
            </div>
          </v-window-item>

          <!-- TAB 6: CLUSTER -->
          <v-window-item value="cluster">
            <ClusterView
              v-if="selected.document_id"
              ref="clusterViewRef"
              :document-id="selected.document_id"
              :sidebar-open="isOpen"
              @view-document="handleViewDocument"
              @comparison-opened="handleComparisonOpened"
            />
          </v-window-item>

          <!-- TAB 7: ASISTENTE DE REDACCIÓN -->
          <v-window-item value="writing">
            <div class="pa-2">
              <v-alert type="info" variant="tonal" class="mb-3">
                <div class="text-subtitle-2 font-weight-medium mb-2">
                  <v-icon size="small" class="mr-1">mdi-lightbulb-on</v-icon>
                  Asistente de Redacción
                </div>
                <div class="text-caption">
                  Obtén ejemplos de buena redacción de secciones específicas de
                  documentos similares a este caso.
                </div>
              </v-alert>

              <!-- Botón para abrir el asistente -->
              <WritingAssistant
                v-if="selected.document_id"
                ref="writingAssistantRef"
                :document-id="selected.document_id"
                :sidebar-open="isOpen"
                @view-document="handleViewDocument"
                @dialog-opened="handleWritingAssistantOpened"
              />

              <!-- Info adicional -->
              <v-card variant="outlined" class="mt-3">
                <v-card-text class="text-caption">
                  <div class="font-weight-medium mb-2">¿Cómo funciona?</div>
                  <ul class="pl-4">
                    <li class="mb-1">
                      Selecciona la sección que deseas redactar
                    </li>
                    <li class="mb-1">El sistema busca documentos similares</li>
                    <li class="mb-1">Extrae ejemplos de buena redacción</li>
                    <li>Te muestra tips de estructura y estilo</li>
                  </ul>
                </v-card-text>
              </v-card>
            </div>
          </v-window-item>
        </v-window>
      </div>

      <!-- Cuando no hay documento -->
      <div v-else class="drawer-content empty">
        <v-alert type="info" variant="tonal">
          Selecciona un documento para ver detalles.
        </v-alert>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import axios from "axios";
import WritingAssistant from "./WritingAssistant.vue";
import ClusterView from "./ClusterView.vue";
import { getSimilarityColor } from "@/composables/useColors";
import { formatDate } from "@/composables/useFormatting";

// ============================================================================
// PROPS & EMITS
// ============================================================================
const props = defineProps({
  selected: Object,
});

const emit = defineEmits([
  "open-chat",
  "select-document",
  "toggle-panel",
  "close-chat",
]);

// ============================================================================
// ESTADO
// ============================================================================
const isOpen = ref(false);
const activeTab = ref("details");
const previousDocumentId = ref(null);

// Referencia al componente ClusterView
const clusterViewRef = ref(null);

// Referencia al componente WritingAssistant
const writingAssistantRef = ref(null);

// Estado para documentos similares
const similarDocs = ref([]);
const loadingSimilar = ref(false);
const similarError = ref(null);

// Estado para análisis modular
const analysisParts = ref([]);
const analyzingDocument = ref(false);
const analysisSuccess = ref(false);
const analysisError = ref(null);

// ============================================================================
// COMPUTED PROPERTIES
// ============================================================================
const fileSizeMB = computed(() => props.selected?.file_size_mb ?? "0.0");

const formattedDate = computed(() =>
  props.selected?.created_at ? formatDate(props.selected.created_at) : "—"
);

const statusColor = computed(() => {
  const colors = {
    processed: "green",
    processing: "amber",
    uploaded: "grey",
    failed: "red",
  };
  return colors[props.selected?.status] || "grey";
});

const statusIcon = computed(() => {
  const icons = {
    processed: "mdi-check-circle",
    processing: "mdi-loading mdi-spin",
    uploaded: "mdi-cloud-upload",
    failed: "mdi-alert-circle",
  };
  return icons[props.selected?.status] || "mdi-help-circle";
});

const statusText = computed(() => {
  const texts = {
    processed: "Procesado",
    processing: "Procesando",
    uploaded: "Subido",
    failed: "Error",
  };
  return texts[props.selected?.status] || props.selected?.status || "—";
});

const validPersons = computed(() => {
  if (!props.selected?.persons) return [];

  return props.selected.persons.filter((person) => {
    const name = person.name || person.person?.name || "";
    return name && name.trim() !== "" && name !== "—";
  });
});

const hasValidPersons = computed(() => validPersons.value.length > 0);
const validPersonsCount = computed(() => validPersons.value.length);

// ============================================================================
// MÉTODOS - PANEL TOGGLE
// ============================================================================

/**
 * Alterna la visibilidad del panel
 */
function togglePanel() {
  isOpen.value = !isOpen.value;

  if (isOpen.value && props.selected) {
    activeTab.value = "details";
  }

  emit("toggle-panel", isOpen.value);
}

/**
 * Abre el panel automáticamente cuando se selecciona un documento
 */
function openDrawerAutomatically() {
  if (props.selected && !isOpen.value) {
    isOpen.value = true;
    activeTab.value = "details";
    emit("toggle-panel", true);
  }
}

// ============================================================================
// MÉTODOS - DOCUMENTOS SIMILARES
// ============================================================================

/**
 * Carga documentos similares al documento actual
 */
async function loadSimilarDocuments() {
  if (!props.selected?.document_id) return;

  similarDocs.value = [];
  loadingSimilar.value = true;
  similarError.value = null;

  try {
    const response = await axios.get(
      `http://localhost:8000/api/documents/${props.selected.document_id}/similar/`,
      {
        params: {
          top_n: 3,
          min_similarity: 0.0, // Siempre obtener top 3, sin importar el score
        },
      }
    );

    if (response.data?.similar_documents) {
      similarDocs.value = response.data.similar_documents;
    }
  } catch (error) {
    console.error("Error loading similar documents:", error);
    similarError.value = "No se pudieron cargar documentos similares";
  } finally {
    loadingSimilar.value = false;
  }
}

/**
 * Formatea las claves del score breakdown para mostrar nombres legibles
 */
function formatScoreKey(key) {
  const translations = {
    semantic_similarity: "Similitud Semántica",
    area_legal_match: "Área Legal Coincidente",
    doc_type_match: "Tipo de Documento",
    legal_subject_match: "Materia Legal",
    person_overlap: "Personas en Común",
    date_proximity: "Cercanía de Fechas",
    penalties: "Penalizaciones",
    metadata_boost: "Boost de Metadatos",
    final_score: "Score Final",
    hybrid_score: "Score Híbrido",
    raw_hybrid_score: "Score Híbrido Crudo",
  };
  return (
    translations[key] ||
    key.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase())
  );
}

/**
 * Retorna el color apropiado para un valor de score en el breakdown
 */
function getScoreColor(value) {
  if (typeof value !== "number") return "grey";

  if (value >= 0.7) return "success";
  if (value >= 0.4) return "info";
  if (value >= 0.1) return "warning";
  if (value < 0) return "error";
  return "grey";
}

/**
 * Maneja el clic en un documento similar
 * Emite el evento para seleccionar ese documento
 */
function handleSimilarDocClick(documentId) {
  if (documentId) {
    emit("select-document", documentId);
  }
}

// ============================================================================
// MÉTODOS - ANÁLISIS MODULAR
// ============================================================================

/**
 * Analiza las partes seleccionadas del documento
 */
async function analyzeDocument() {
  if (!props.selected?.document_id || analysisParts.value.length === 0) return;

  analyzingDocument.value = true;
  analysisSuccess.value = false;
  analysisError.value = null;

  try {
    const response = await axios.post(
      `http://localhost:8000/api/documents/${props.selected.document_id}/analyze/`,
      {
        parts: analysisParts.value,
      },
      {
        headers: {
          "Content-Type": "application/json",
        },
      }
    );

    if (response.data) {
      analysisSuccess.value = true;
      analysisParts.value = []; // Limpiar selección

      // Emitir evento para actualizar el documento
      emit("select-document", props.selected.document_id);

      // Ocultar mensaje de éxito después de 3 segundos
      setTimeout(() => {
        analysisSuccess.value = false;
      }, 3000);
    }
  } catch (error) {
    console.error("Error analyzing document:", error);
    analysisError.value =
      error.response?.data?.error || "No se pudo completar el análisis";
  } finally {
    analyzingDocument.value = false;
  }
}

/**
 * Retorna el color según el estado del análisis
 */
function getAnalysisStatusColor(part) {
  const status = props.selected?.analysis_status?.[part];
  const colors = {
    pending: "grey",
    processing: "warning",
    completed: "success",
    failed: "error",
  };
  return colors[status] || "grey";
}

/**
 * Retorna el icono según el estado del análisis
 */
function getAnalysisStatusIcon(part) {
  const status = props.selected?.analysis_status?.[part];
  const icons = {
    pending: "mdi-clock-outline",
    processing: "mdi-loading mdi-spin",
    completed: "mdi-check-circle",
    failed: "mdi-alert-circle",
  };
  return icons[status] || "mdi-help-circle";
}

/**
 * Retorna el texto según el estado del análisis
 */
function getAnalysisStatusText(part) {
  const status = props.selected?.analysis_status?.[part];
  const texts = {
    pending: "Pendiente",
    processing: "Procesando...",
    completed: "Completado",
    failed: "Error",
  };
  return texts[status] || "Desconocido";
}

/**
 * Retorna la clase CSS según el estado del análisis
 */
function getAnalysisCardClass(part) {
  const status = props.selected?.analysis_status?.[part];
  return status === "completed" ? "analysis-completed" : "";
}

// ============================================================================
// MÉTODOS - ASISTENTE DE REDACCIÓN
// ============================================================================

/**
 * Maneja el evento de ver documento desde el asistente de redacción
 */
function handleViewDocument(documentId) {
  emit("select-document", documentId);
  // Cambiar a la tab de detalles para mostrar el nuevo documento
  activeTab.value = "details";
}

/**
 * Maneja el evento de abrir chat
 * Cierra el diálogo de comparación del cluster y el asistente de redacción si están abiertos
 */
function handleOpenChat() {
  // Cerrar el diálogo de comparación si existe
  if (clusterViewRef.value) {
    clusterViewRef.value.closeComparison();
  }
  // Cerrar el asistente de redacción si existe
  if (writingAssistantRef.value) {
    writingAssistantRef.value.close();
  }
  // Emitir el evento para abrir el chat
  emit("open-chat");
}

/**
 * Maneja el evento cuando se abre el diálogo de comparación del cluster
 * Cierra el chat y el asistente de redacción si están abiertos
 */
function handleComparisonOpened() {
  // Cerrar el chat
  emit("close-chat");
  // Cerrar el asistente de redacción si existe
  if (writingAssistantRef.value) {
    writingAssistantRef.value.close();
  }
}

/**
 * Maneja el evento cuando se abre el asistente de redacción
 * Cierra el chat y el diálogo de comparación si están abiertos
 */
function handleWritingAssistantOpened() {
  // Cerrar el chat
  emit("close-chat");
  // Cerrar el diálogo de comparación si existe
  if (clusterViewRef.value) {
    clusterViewRef.value.closeComparison();
  }
}

// ============================================================================
// MÉTODOS - UTILIDADES
// ============================================================================

/**
 * Abre el documento en una nueva pestaña
 */
function openPreview() {
  if (props.selected?.file_path) {
    const fileUrl = props.selected.file_path.startsWith("/")
      ? props.selected.file_path
      : "/" + props.selected.file_path;
    window.open(fileUrl, "_blank");
  }
}

/**
 * Retorna el color según el rol de la persona
 */
function getRoleColor(role) {
  const colors = {
    Demandante: "blue",
    Demandado: "red",
    Juez: "purple",
    Fiscal: "green",
    Abogado: "orange",
    Testigo: "teal",
    Perito: "indigo",
    Tercero: "grey",
  };
  return colors[role] || "grey";
}

/**
 * Extrae las razones de similitud legibles desde el array de objetos JSON
 */
function getSimilarityReasons(simDoc) {
  if (!simDoc.similarity_reasons || !Array.isArray(simDoc.similarity_reasons)) {
    return [];
  }

  return simDoc.similarity_reasons.map((reason) => {
    // Si ya es un string, devolverlo directamente
    if (typeof reason === "string") {
      return reason;
    }
    // Si es un objeto con la propiedad 'detail', extraerla
    if (typeof reason === "object" && reason !== null && reason.detail) {
      return reason.detail;
    }
    // Fallback: convertir a JSON (por si acaso)
    return JSON.stringify(reason);
  });
}

// ============================================================================
// WATCHERS
// ============================================================================

/**
 * Watcher principal para detectar cambios en el documento seleccionado
 * Maneja la apertura/cierre del drawer y carga de datos relacionados
 */
watch(
  () => props.selected,
  (newDoc) => {
    // Sin documento: limpiar y cerrar
    if (!newDoc) {
      similarDocs.value = [];
      isOpen.value = false;
      previousDocumentId.value = null;
      emit("toggle-panel", false);
      return;
    }

    const newId = newDoc?.document_id;
    const wasReselected = newDoc?._reselected;

    // Re-selección: toggle del drawer
    if (wasReselected && newId === previousDocumentId.value) {
      isOpen.value = !isOpen.value;
      emit("toggle-panel", isOpen.value);
    } else {
      // Nuevo documento: abrir y cargar datos
      previousDocumentId.value = newId;

      if (!isOpen.value) {
        openDrawerAutomatically();
      }

      if (newId) {
        loadSimilarDocuments();
      }
    }
  },
  { deep: true }
);
</script>

<style scoped lang="sass">
/* ===== 🎨 Panel Container ===== */
.doc-details-panel
  position: relative
  height: 100%
  width: 100%
  background-color: rgb(var(--v-theme-surface))
  border-left: 1px solid rgba(var(--v-border-color), 0.2)
  overflow: hidden

/* ===== 📦 Panel Content ===== */
.panel-container
  height: 100%
  width: 100%
  overflow: hidden

.drawer-content
  height: 100%
  padding: 16px
  padding-right: 60px
  overflow-y: auto
  display: flex
  flex-direction: column

  &::-webkit-scrollbar
    width: 8px

  &::-webkit-scrollbar-track
    background: rgba(var(--v-theme-surface-variant), 0.3)
    border-radius: 4px

  &::-webkit-scrollbar-thumb
    background: rgba(var(--v-theme-primary), 0.4)
    border-radius: 4px

    &:hover
      background: rgba(var(--v-theme-primary), 0.6)

.empty
  display: flex
  align-items: center
  justify-content: center
  flex: 1

/* ===== 🔘 Toggle Button ===== */
.toggle-btn
  position: absolute
  top: 16px
  left: -22px  // Mitad del ancho del botón (44px / 2)
  z-index: 10
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1)
  font-weight: 500
  width: 44px !important
  min-width: 44px !important
  height: 44px !important
  padding: 0 !important
  border-radius: 50%
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15)

  &:hover
    transform: scale(1.1)
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2)

  .v-icon
    margin: 0 !important

/* ===== 🎭 Transitions ===== */
.fade-enter-active, .fade-leave-active
  transition: opacity 0.3s ease

.fade-enter-from, .fade-leave-to
  opacity: 0

/* ===== 📄 Documentos Similares ===== */
.similar-docs-container
  max-height: calc(100vh - 320px)
  overflow-y: auto

.similar-doc-card
  cursor: pointer
  border-radius: 12px
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1)
  border: 1.5px solid rgba(var(--v-border-color), 0.2)
  background-color: rgb(var(--v-theme-surface))

  &:hover
    transform: translateY(-2px)
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12)
    border-color: rgb(var(--v-theme-primary))
    background-color: rgba(var(--v-theme-primary), 0.02)

    .similar-title
      color: rgb(var(--v-theme-primary))

  &:active
    transform: translateY(0)
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08)

.similar-title
  line-height: 1.4
  transition: color 0.2s ease
  display: -webkit-box
  -webkit-line-clamp: 2
  -webkit-box-orient: vertical
  overflow: hidden

.similarity-chip
  font-weight: 600
  letter-spacing: 0.3px

.gap-1
  gap: 4px

/* ===== 📝 Summary Content ===== */
.summary-content
  max-height: 500px
  overflow-y: auto
  padding: 8px
  background-color: rgba(var(--v-theme-surface-variant), 0.2)
  border-radius: 8px

  &::-webkit-scrollbar
    width: 6px

  &::-webkit-scrollbar-track
    background: rgba(var(--v-theme-surface-variant), 0.3)
    border-radius: 3px

  &::-webkit-scrollbar-thumb
    background: rgba(var(--v-theme-primary), 0.4)
    border-radius: 3px

    &:hover
      background: rgba(var(--v-theme-primary), 0.6)

/* ===== 👥 Personas Grid ===== */
.persons-grid
  max-height: 500px
  overflow-y: auto

  &::-webkit-scrollbar
    width: 6px

  &::-webkit-scrollbar-track
    background: rgba(var(--v-theme-surface-variant), 0.3)
    border-radius: 3px

  &::-webkit-scrollbar-thumb
    background: rgba(var(--v-theme-primary), 0.4)
    border-radius: 3px

    &:hover
      background: rgba(var(--v-theme-primary), 0.6)

.person-card
  transition: all 0.2s ease
  cursor: default

  &:hover
    transform: translateY(-2px)
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1)

/* ===== 🔍 Análisis Modular ===== */
.analysis-options
  .v-card
    transition: all 0.2s ease

.analysis-completed
  background-color: rgba(var(--v-theme-success), 0.05)
  border-color: rgba(var(--v-theme-success), 0.3)

/* ===== 📱 Responsive ===== */
@media (max-width: 960px)
  .toggle-btn
    left: -52px  // Más fuera en mobile para que sea visible
</style>
