<template>
  <v-container
    fluid
    class="clusters-view-echarts pa-4"
    style="max-width: 1920px; margin: 0 auto"
  >
    <!-- Header Row -->
    <v-row class="mb-3">
      <v-col cols="12">
        <div class="d-flex align-center justify-space-between">
          <div class="d-flex align-center">
            <v-icon size="large" class="mr-2" color="primary"
              >mdi-chart-bubble</v-icon
            >
            <div>
              <h1 class="text-h5 font-weight-bold mb-0">
                Explorador de Clusters
              </h1>
              <p class="text-caption text-grey mb-0">
                Mapa visual de documentos agrupados por similitud semántica
              </p>
            </div>
          </div>
          <div class="d-flex gap-2 align-center">
            <!-- Compact Stats -->
            <v-chip
              v-if="metadata"
              size="small"
              color="primary"
              variant="tonal"
            >
              <v-icon start size="small">mdi-file-document-multiple</v-icon>
              {{ metadata.document_count }} docs
            </v-chip>
            <v-chip
              v-if="metadata"
              size="small"
              color="success"
              variant="tonal"
            >
              <v-icon start size="small">mdi-chart-bubble</v-icon>
              {{ metadata.cluster_count }} clusters
            </v-chip>
            <v-chip
              v-if="metadata && metadata.noise_count > 0"
              size="small"
              color="warning"
              variant="tonal"
            >
              <v-icon start size="small">mdi-help-circle</v-icon>
              {{ metadata.noise_count }} sin grupo
            </v-chip>
            <v-divider vertical class="mx-2"></v-divider>
            <v-chip
              v-if="metadata"
              size="small"
              variant="outlined"
              prepend-icon="mdi-clock-outline"
            >
              {{ formatDate(metadata.created_at) }}
            </v-chip>
            <v-btn
              color="primary"
              size="small"
              prepend-icon="mdi-refresh"
              @click="regenerateClusters"
              :loading="regenerating"
              :disabled="regenerating"
            >
              {{ regenerating ? "Regenerando..." : "Recargar" }}
            </v-btn>
          </div>
        </div>
      </v-col>
    </v-row>

    <!-- Regeneration Progress Alert -->
    <v-row v-if="regenerationProgress" class="mb-2">
      <v-col cols="12">
        <v-alert
          type="info"
          variant="tonal"
          density="compact"
          closable
          @click:close="regenerationProgress = null"
        >
          <div class="d-flex align-center">
            <v-progress-circular
              v-if="!regenerationProgress.completed"
              indeterminate
              size="16"
              width="2"
              class="mr-2"
            ></v-progress-circular>
            <v-icon v-else color="success" size="small" class="mr-2"
              >mdi-check-circle</v-icon
            >
            <span class="font-weight-medium">{{
              regenerationProgress.message
            }}</span>
            <span v-if="regenerationProgress.details" class="text-caption ml-2">
              {{ regenerationProgress.details }}
            </span>
          </div>
        </v-alert>
      </v-col>
    </v-row>

    <!-- Main Content: Graph (Left) + Sidebar (Right) -->
    <v-row>
      <!-- Graph Panel - Takes ~70% -->
      <v-col cols="12" lg="8" xl="9">
        <v-card elevation="2" class="graph-card">
          <v-card-title
            class="bg-grey-lighten-4 py-2 d-flex justify-space-between align-center"
          >
            <div class="d-flex align-center">
              <v-icon class="mr-2" size="small">mdi-graph</v-icon>
              <span class="text-subtitle-1 font-weight-medium"
                >Vista de Clusters</span
              >
              <v-chip
                v-if="selectedCluster !== null"
                size="x-small"
                color="primary"
                class="ml-2"
                closable
                @click:close="clearFilter"
              >
                Cluster {{ selectedCluster }}
              </v-chip>
            </div>
            <div class="d-flex gap-1 align-center">
              <v-switch
                v-model="showEdges"
                density="compact"
                hide-details
                color="primary"
                class="compact-switch"
              >
                <template v-slot:label>
                  <span class="text-caption">Conexiones</span>
                </template>
              </v-switch>
              <v-switch
                v-model="useForceLayout"
                density="compact"
                hide-details
                color="secondary"
                class="compact-switch"
              >
                <template v-slot:label>
                  <span class="text-caption">Auto-agrupar</span>
                </template>
              </v-switch>
              <v-divider vertical class="mx-1"></v-divider>
              <div style="width: 120px">
                <v-slider
                  v-model="topK"
                  :min="2"
                  :max="15"
                  :step="1"
                  density="compact"
                  hide-details
                  color="primary"
                  @update:modelValue="onTopKChange"
                  thumb-label
                >
                  <template v-slot:prepend>
                    <span class="text-caption text-grey">K:{{ topK }}</span>
                  </template>
                </v-slider>
              </div>
              <v-btn-group density="compact" variant="outlined" class="ml-1">
                <v-btn
                  size="x-small"
                  icon="mdi-magnify-plus"
                  @click="zoomIn"
                ></v-btn>
                <v-btn
                  size="x-small"
                  icon="mdi-magnify-minus"
                  @click="zoomOut"
                ></v-btn>
                <v-btn
                  size="x-small"
                  icon="mdi-fit-to-screen"
                  @click="fitToView"
                ></v-btn>
              </v-btn-group>
            </div>
          </v-card-title>

          <v-card-text class="pa-0" style="position: relative">
            <div
              v-if="loading"
              class="d-flex align-center justify-center"
              style="height: 550px"
            >
              <div class="text-center">
                <v-progress-circular
                  indeterminate
                  color="primary"
                  size="48"
                ></v-progress-circular>
                <div class="mt-3 text-subtitle-2">Cargando clusters...</div>
              </div>
            </div>
            <div
              v-show="!loading"
              ref="chartContainer"
              class="chart-container"
              style="width: 100%; height: 550px"
            ></div>
          </v-card-text>
        </v-card>

        <!-- Quality Metrics - Compact horizontal row below graph -->
        <v-card
          v-if="qualityMetrics && !qualityMetrics.error"
          elevation="1"
          class="mt-3"
        >
          <v-card-text class="py-2">
            <div
              class="d-flex align-center justify-space-between flex-wrap gap-3"
            >
              <div class="d-flex align-center">
                <v-icon size="small" class="mr-2" color="grey"
                  >mdi-chart-areaspline</v-icon
                >
                <span class="text-caption font-weight-medium text-grey-darken-1"
                  >Métricas de Calidad:</span
                >
              </div>

              <!-- Silhouette -->
              <div class="d-flex align-center metric-item">
                <v-avatar
                  size="24"
                  :color="getSilhouetteColor(qualityMetrics.silhouette_score)"
                  class="mr-1"
                >
                  <v-icon size="x-small" color="white"
                    >mdi-circle-slice-8</v-icon
                  >
                </v-avatar>
                <div>
                  <span class="text-caption text-grey">Silhouette</span>
                  <div class="text-subtitle-2 font-weight-bold">
                    {{ qualityMetrics.silhouette_score?.toFixed(3) ?? "N/A" }}
                  </div>
                </div>
                <v-tooltip activator="parent" location="bottom">
                  <div style="max-width: 200px">
                    {{ qualityMetrics.interpretation?.silhouette?.message
                    }}<br />
                    <small>Rango: -1 a 1 (mayor es mejor)</small>
                  </div>
                </v-tooltip>
              </div>

              <!-- Calinski-Harabasz -->
              <div class="d-flex align-center metric-item">
                <v-avatar size="24" color="primary" class="mr-1">
                  <v-icon size="x-small" color="white"
                    >mdi-chart-scatter-plot</v-icon
                  >
                </v-avatar>
                <div>
                  <span class="text-caption text-grey">Calinski-Harabasz</span>
                  <div class="text-subtitle-2 font-weight-bold">
                    {{
                      qualityMetrics.calinski_harabasz_score?.toFixed(1) ??
                      "N/A"
                    }}
                  </div>
                </div>
                <v-tooltip activator="parent" location="bottom">
                  <div style="max-width: 200px">
                    {{
                      qualityMetrics.interpretation?.calinski_harabasz?.message
                    }}<br />
                    <small>Sin límite superior (mayor es mejor)</small>
                  </div>
                </v-tooltip>
              </div>

              <!-- Davies-Bouldin -->
              <div class="d-flex align-center metric-item">
                <v-avatar
                  size="24"
                  :color="
                    getDaviesBouldinColor(qualityMetrics.davies_bouldin_score)
                  "
                  class="mr-1"
                >
                  <v-icon size="x-small" color="white">mdi-target</v-icon>
                </v-avatar>
                <div>
                  <span class="text-caption text-grey">Davies-Bouldin</span>
                  <div class="text-subtitle-2 font-weight-bold">
                    {{
                      qualityMetrics.davies_bouldin_score?.toFixed(3) ?? "N/A"
                    }}
                  </div>
                </div>
                <v-tooltip activator="parent" location="bottom">
                  <div style="max-width: 200px">
                    {{ qualityMetrics.interpretation?.davies_bouldin?.message
                    }}<br />
                    <small>Rango: 0+ (menor es mejor)</small>
                  </div>
                </v-tooltip>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- Sidebar - Takes ~30% -->
      <v-col cols="12" lg="4" xl="3">
        <!-- SEARCH PANEL -->
        <v-card elevation="2" class="mb-3">
          <v-card-title class="bg-primary py-2 d-flex align-center">
            <v-icon class="mr-2" size="small" color="white">mdi-magnify</v-icon>
            <span class="text-subtitle-1 font-weight-medium text-white"
              >Búsqueda Semántica</span
            >
            <v-spacer></v-spacer>
            <v-btn
              v-if="searchResults.length > 0"
              icon="mdi-close"
              variant="text"
              color="white"
              size="x-small"
              @click="clearSearch"
            ></v-btn>
          </v-card-title>

          <v-card-text class="pa-3">
            <!-- Search Tabs -->
            <v-tabs
              v-model="searchTab"
              density="compact"
              color="primary"
              class="mb-3"
            >
              <v-tab value="text" size="small">
                <v-icon start size="small">mdi-text-search</v-icon>
                Texto
              </v-tab>
              <v-tab value="file" size="small">
                <v-icon start size="small">mdi-file-upload</v-icon>
                Documento
              </v-tab>
            </v-tabs>

            <v-window v-model="searchTab">
              <!-- Text Search Tab -->
              <v-window-item value="text">
                <v-textarea
                  v-model="searchQuery"
                  label="Buscar documentos similares"
                  placeholder="Escribe una oración o párrafo para encontrar documentos similares..."
                  variant="outlined"
                  density="compact"
                  rows="3"
                  hide-details
                  class="mb-2"
                  @keydown.ctrl.enter="performSearch"
                ></v-textarea>
                <v-btn
                  color="primary"
                  block
                  :loading="searchLoading"
                  :disabled="!searchQuery || searchLoading"
                  @click="performSearch"
                  prepend-icon="mdi-magnify"
                >
                  Buscar en Clusters
                </v-btn>
              </v-window-item>

              <!-- File Upload Tab -->
              <v-window-item value="file">
                <v-file-input
                  v-model="searchFile"
                  label="Subir documento"
                  placeholder="Selecciona un archivo PDF o TXT"
                  variant="outlined"
                  density="compact"
                  accept=".pdf,.txt,.md,.text"
                  prepend-icon="mdi-paperclip"
                  hide-details
                  class="mb-2"
                  @update:model-value="onFileSelected"
                ></v-file-input>
                <div class="text-caption text-grey mb-2">
                  Soporta archivos PDF y de texto (.txt, .md)
                </div>
                <v-btn
                  color="primary"
                  block
                  :loading="searchLoading"
                  :disabled="
                    !searchFile ||
                    (Array.isArray(searchFile) && searchFile.length === 0) ||
                    searchLoading
                  "
                  @click="performFileSearch"
                  prepend-icon="mdi-file-search"
                >
                  Buscar Similares
                </v-btn>
              </v-window-item>
            </v-window>

            <!-- Search Options -->
            <div class="d-flex align-center mt-3 gap-2">
              <v-slider
                v-model="searchTopN"
                :min="5"
                :max="30"
                :step="5"
                density="compact"
                hide-details
                color="primary"
                thumb-label
                class="flex-grow-1"
              >
                <template v-slot:prepend>
                  <span class="text-caption text-grey"
                    >Top {{ searchTopN }}</span
                  >
                </template>
              </v-slider>
            </div>
          </v-card-text>

          <!-- Search Results Summary -->
          <v-expand-transition>
            <div v-if="searchResults.length > 0">
              <v-divider></v-divider>
              <v-card-text class="pa-2 bg-amber-lighten-5">
                <div class="d-flex align-center justify-space-between">
                  <div class="d-flex align-center">
                    <v-icon color="amber-darken-2" size="small" class="mr-1"
                      >mdi-star</v-icon
                    >
                    <span class="text-caption font-weight-medium">
                      {{ searchResults.length }} documentos encontrados
                    </span>
                  </div>
                  <v-chip
                    v-if="dominantSearchCluster !== null"
                    size="x-small"
                    :color="getClusterColor(dominantSearchCluster)"
                    @click="filterByCluster(dominantSearchCluster)"
                  >
                    Cluster {{ dominantSearchCluster }} ({{
                      dominantSearchClusterCount
                    }})
                  </v-chip>
                </div>
                <v-progress-linear
                  :model-value="searchResults[0]?.similarity * 100 || 0"
                  color="amber-darken-2"
                  height="6"
                  rounded
                  class="mt-1"
                >
                  <template v-slot:default>
                    <span class="text-caption text-white">
                      Max:
                      {{
                        ((searchResults[0]?.similarity || 0) * 100).toFixed(1)
                      }}%
                    </span>
                  </template>
                </v-progress-linear>
              </v-card-text>
            </div>
          </v-expand-transition>
        </v-card>

        <!-- Main Sidebar Card -->
        <v-card
          elevation="2"
          class="sidebar-card"
          :style="{
            height: searchResults.length > 0 ? '400px' : '620px',
            display: 'flex',
            flexDirection: 'column',
          }"
        >
          <!-- SEARCH RESULTS VIEW -->
          <template v-if="searchResults.length > 0 && selectedCluster === null">
            <v-card-title class="bg-amber-darken-2 py-2 flex-shrink-0">
              <v-icon class="mr-2" size="small" color="white"
                >mdi-file-search</v-icon
              >
              <span class="text-subtitle-1 font-weight-medium text-white"
                >Resultados</span
              >
              <v-spacer></v-spacer>
              <v-btn
                icon="mdi-close"
                variant="text"
                color="white"
                size="x-small"
                @click="clearSearch"
              ></v-btn>
            </v-card-title>

            <div
              class="search-results-section flex-grow-1"
              style="overflow-y: auto"
            >
              <v-list density="compact" class="pa-0">
                <v-list-item
                  v-for="(result, index) in searchResults"
                  :key="result.id"
                  @click="openSearchResult(result)"
                  @mouseenter="highlightNodeInChart(result.id)"
                  @mouseleave="clearNodeHighlight()"
                  class="search-result-item"
                  :class="{ 'bg-amber-lighten-5': index < 3 }"
                >
                  <template v-slot:prepend>
                    <div class="d-flex flex-column align-center mr-2">
                      <v-avatar
                        :color="getSearchResultColor(result.similarity)"
                        size="28"
                      >
                        <span class="text-white text-caption font-weight-bold">
                          {{ index + 1 }}
                        </span>
                      </v-avatar>
                      <v-chip
                        size="x-small"
                        :color="getClusterColor(result.cluster)"
                        class="mt-1"
                        style="font-size: 9px"
                      >
                        {{
                          result.cluster !== null &&
                          result.cluster !== undefined
                            ? `C${result.cluster}`
                            : "N/A"
                        }}
                      </v-chip>
                    </div>
                  </template>

                  <v-list-item-title class="text-body-2 font-weight-medium">
                    {{ result.title || "Sin título" }}
                  </v-list-item-title>
                  <v-list-item-subtitle class="text-caption">
                    <span v-if="result.case_number"
                      >📁 {{ result.case_number }}</span
                    >
                    <span v-if="result.legal_area" class="ml-1"
                      >⚖️ {{ result.legal_area }}</span
                    >
                  </v-list-item-subtitle>

                  <template v-slot:append>
                    <div class="text-right">
                      <div
                        class="text-caption font-weight-bold"
                        :style="{
                          color: getSearchResultColor(result.similarity),
                        }"
                      >
                        {{ (result.similarity * 100).toFixed(1) }}%
                      </div>
                      <v-progress-linear
                        :model-value="result.similarity * 100"
                        :color="getSearchResultColor(result.similarity)"
                        height="4"
                        rounded
                        style="width: 50px"
                      ></v-progress-linear>
                    </div>
                  </template>
                </v-list-item>
              </v-list>
            </div>
          </template>

          <!-- CLUSTERS VIEW (when no cluster selected and no search results) -->
          <template v-else-if="selectedCluster === null">
            <v-card-title class="bg-grey-lighten-4 py-2 flex-shrink-0">
              <v-icon class="mr-2" size="small">mdi-chart-bar</v-icon>
              <span class="text-subtitle-1 font-weight-medium">Clusters</span>
              <v-spacer></v-spacer>
              <v-chip size="x-small" color="primary" variant="tonal">
                {{ clusterStats?.length || 0 }} grupos
              </v-chip>
            </v-card-title>

            <div class="cluster-list-section flex-grow-1">
              <v-list density="compact" class="pa-0">
                <v-list-item
                  v-for="stat in clusterStats"
                  :key="stat.cluster_label"
                  @click="filterByCluster(stat.cluster_label)"
                  class="cluster-list-item"
                >
                  <template v-slot:prepend>
                    <v-avatar
                      :color="getClusterColor(stat.cluster_label)"
                      size="28"
                    >
                      <span class="text-white text-caption font-weight-bold">{{
                        stat.cluster_label
                      }}</span>
                    </v-avatar>
                  </template>

                  <v-list-item-title class="text-body-2">
                    {{ stat.main_area }}
                  </v-list-item-title>
                  <v-list-item-subtitle class="text-caption">
                    {{ stat.size }} documentos
                  </v-list-item-subtitle>

                  <template v-slot:append>
                    <v-chip size="x-small" color="grey" variant="tonal">
                      {{ stat.size }}
                    </v-chip>
                  </template>
                </v-list-item>
              </v-list>
            </div>
          </template>

          <!-- DOCUMENTS VIEW (when cluster is selected) -->
          <template v-else>
            <!-- Header with back button -->
            <div class="bg-primary pa-2 d-flex align-center flex-shrink-0">
              <v-btn
                icon="mdi-arrow-left"
                variant="text"
                color="white"
                size="small"
                @click="clearFilter"
                class="mr-2"
              ></v-btn>
              <v-avatar
                :color="getClusterColor(selectedCluster)"
                size="28"
                class="mr-2"
              >
                <span class="text-white text-caption font-weight-bold">{{
                  selectedCluster
                }}</span>
              </v-avatar>
              <div class="text-white flex-grow-1">
                <div class="text-subtitle-2 font-weight-medium">
                  {{
                    selectedClusterStats?.main_area ||
                    "Cluster " + selectedCluster
                  }}
                </div>
                <div class="text-caption" style="opacity: 0.8">
                  {{ selectedClusterDocuments.length }} documentos
                </div>
              </div>
              <v-btn
                icon="mdi-close"
                variant="text"
                color="white"
                size="x-small"
                @click="clearFilter"
              ></v-btn>
            </div>

            <!-- Area Distribution Tags -->
            <div
              class="pa-2 bg-grey-lighten-4 flex-shrink-0"
              v-if="selectedClusterStats?.area_distribution"
            >
              <div class="d-flex gap-1 flex-wrap">
                <v-chip
                  v-for="(
                    count, area
                  ) in selectedClusterStats.area_distribution"
                  :key="area"
                  size="x-small"
                  variant="flat"
                  :color="
                    area === selectedClusterStats.main_area
                      ? 'primary'
                      : 'grey-lighten-1'
                  "
                >
                  {{ area }}: {{ count }}
                </v-chip>
              </div>
            </div>

            <!-- Documents List -->
            <div
              class="documents-list-section flex-grow-1"
              style="min-height: 0"
            >
              <v-virtual-scroll
                :items="selectedClusterDocuments"
                :item-height="56"
                class="fill-height"
              >
                <template v-slot:default="{ item, index }">
                  <v-list-item
                    :key="item.id"
                    @click="openDocumentDetails(item)"
                    @mouseenter="highlightNodeInGraph(item.id)"
                    @mouseleave="unhighlightNodeInGraph()"
                    class="cluster-doc-item px-2"
                    :class="{ 'bg-grey-lighten-5': index % 2 === 0 }"
                    density="compact"
                  >
                    <v-list-item-title
                      class="text-body-2 font-weight-medium text-truncate"
                    >
                      {{ item.title || "Documento sin título" }}
                    </v-list-item-title>
                    <v-list-item-subtitle class="text-caption">
                      <span v-if="item.case_number"
                        >📁 {{ item.case_number }}</span
                      >
                      <span v-if="item.legal_area" class="ml-2"
                        >⚖️ {{ item.legal_area }}</span
                      >
                    </v-list-item-subtitle>

                    <template v-slot:append>
                      <v-btn
                        icon="mdi-eye-outline"
                        variant="text"
                        color="primary"
                        size="x-small"
                        @click.stop="openDocumentDetails(item)"
                      ></v-btn>
                    </template>
                  </v-list-item>
                </template>
              </v-virtual-scroll>
            </div>
          </template>
        </v-card>
      </v-col>
    </v-row>

    <!-- Document Details Dialog -->
    <v-dialog v-model="showDetails" max-width="700">
      <v-card v-if="selectedDocument">
        <v-card-title class="bg-primary text-white py-3">
          <div
            class="d-flex justify-space-between align-center"
            style="width: 100%"
          >
            <span
              class="text-subtitle-1 text-truncate"
              style="max-width: 500px"
            >
              {{ selectedDocument.title }}
            </span>
            <v-btn
              icon="mdi-close"
              variant="text"
              color="white"
              size="small"
              @click="showDetails = false"
            ></v-btn>
          </div>
        </v-card-title>
        <v-card-text class="pa-4">
          <v-row dense>
            <v-col cols="6">
              <div class="text-caption text-grey">Expediente</div>
              <div class="text-body-2 font-weight-medium">
                {{ selectedDocument.case_number || "N/A" }}
              </div>
            </v-col>
            <v-col cols="6">
              <div class="text-caption text-grey">Área Legal</div>
              <div class="text-body-2 font-weight-medium">
                {{ selectedDocument.legal_area || "N/A" }}
              </div>
            </v-col>
            <v-col cols="6">
              <div class="text-caption text-grey">Tipo</div>
              <div class="text-body-2 font-weight-medium">
                {{ selectedDocument.doc_type || "N/A" }}
              </div>
            </v-col>
            <v-col cols="6">
              <div class="text-caption text-grey">Cluster</div>
              <v-chip
                size="small"
                :color="getClusterColor(selectedDocument.cluster)"
              >
                {{ selectedDocument.cluster }}
              </v-chip>
            </v-col>
            <v-col v-if="selectedDocument.document_date" cols="6">
              <div class="text-caption text-grey">Fecha</div>
              <div class="text-body-2 font-weight-medium">
                {{ formatDate(selectedDocument.document_date) }}
              </div>
            </v-col>
          </v-row>

          <!-- Action Button: Chat with Document -->
          <v-tooltip
            location="bottom"
            text="Abrir en nueva pestaña para analizar con IA"
          >
            <template v-slot:activator="{ props }">
              <v-btn
                v-bind="props"
                color="primary"
                size="large"
                block
                class="mt-4"
                prepend-icon="mdi-chat-processing"
                @click="openDocumentChat(selectedDocument)"
              >
                Chat con Documento
                <v-icon end size="small">mdi-open-in-new</v-icon>
              </v-btn>
            </template>
          </v-tooltip>

          <!-- Related Documents -->
          <template v-if="selectedDocumentNeighbors.length > 0">
            <v-divider class="my-4"></v-divider>
            <div class="text-subtitle-2 mb-2">
              📎 Documentos Relacionados ({{
                selectedDocumentNeighbors.length
              }})
            </div>
            <v-list
              density="compact"
              class="pa-0"
              style="max-height: 200px; overflow-y: auto"
            >
              <v-list-item
                v-for="neighbor in selectedDocumentNeighbors"
                :key="neighbor.id"
                class="px-0"
                @click="openDocumentChat(neighbor)"
                style="cursor: pointer"
              >
                <template v-slot:prepend>
                  <v-chip
                    size="x-small"
                    :color="getClusterColor(neighbor.cluster)"
                    class="mr-2"
                  >
                    {{ neighbor.cluster }}
                  </v-chip>
                </template>
                <v-list-item-title class="text-body-2">{{
                  neighbor.title
                }}</v-list-item-title>
                <v-list-item-subtitle class="text-caption">
                  {{ (neighbor.similarity * 100).toFixed(1) }}% similar •
                  {{ neighbor.case_number || "Sin expediente" }}
                </v-list-item-subtitle>
                <template v-slot:append>
                  <v-progress-linear
                    :model-value="neighbor.similarity * 100"
                    height="4"
                    color="primary"
                    style="width: 60px"
                  ></v-progress-linear>
                </template>
              </v-list-item>
            </v-list>
          </template>
        </v-card-text>
        <v-card-actions class="px-4 pb-4">
          <v-btn
            variant="outlined"
            color="primary"
            prepend-icon="mdi-open-in-new"
            @click="openDocumentChat(selectedDocument)"
          >
            Ver Análisis Completo
          </v-btn>
          <v-spacer></v-spacer>
          <v-btn variant="text" @click="showDetails = false">Cerrar</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, computed, nextTick } from "vue";
import { useRouter } from "vue-router";
import axios from "axios";
import * as echarts from "echarts";
import * as pdfjsLib from "pdfjs-dist";
import pdfjsWorker from "pdfjs-dist/build/pdf.worker.min.mjs?url";

// Configure PDF.js worker for Vite
pdfjsLib.GlobalWorkerOptions.workerSrc = pdfjsWorker;

const router = useRouter();

// State
const loading = ref(false);
const regenerating = ref(false);
const regenerationProgress = ref(null);
const showEdges = ref(true);
const useForceLayout = ref(true);
const showDetails = ref(false);
const selectedDocument = ref(null);
const selectedDocumentNeighbors = ref([]);
const selectedCluster = ref(null);
const topK = ref(5);

// Search State
const searchTab = ref("text");
const searchQuery = ref("");
const searchFile = ref(null);
const searchLoading = ref(false);
const searchResults = ref([]); // Array of {id, title, similarity, cluster, ...}
const searchTopN = ref(15);
const searchResultIds = ref(new Set()); // For quick lookup when highlighting
const fileInputRef = ref(null); // Reference for file input element

// Data from API
const nodes = ref([]);
const links = ref([]);
const clusterStats = ref([]);
const metadata = ref(null);
const qualityMetrics = ref(null);

// ECharts refs
const chartContainer = ref(null);
let chartInstance = null;
let resizeObserver = null;

// Professional color palette for clusters - Vibrant, high contrast, colorblind-friendly
const clusterColors = [
  "#2563EB", // Royal Blue
  "#DC2626", // Crimson Red
  "#059669", // Emerald
  "#7C3AED", // Vivid Purple
  "#EA580C", // Burnt Orange
  "#0891B2", // Teal Cyan
  "#C026D3", // Fuchsia
  "#CA8A04", // Gold
  "#4F46E5", // Indigo
  "#16A34A", // Kelly Green
  "#E11D48", // Rose
  "#0D9488", // Dark Teal
  "#9333EA", // Violet
  "#F97316", // Bright Orange
  "#0284C7", // Sky Blue
  "#65A30D", // Lime Green
  "#DB2777", // Hot Pink
  "#1D4ED8", // Deep Blue
  "#B91C1C", // Dark Red
  "#047857", // Forest Green
];

// Get cluster color with improved contrast
const getClusterColor = (cluster) => {
  if (cluster === -1) return "#6B7280"; // Neutral gray for noise
  return clusterColors[Math.abs(cluster) % clusterColors.length];
};

// Helper functions for quality metrics visualization
const getSilhouetteColor = (score) => {
  if (score === null || score === undefined) return "grey";
  if (score >= 0.7) return "success";
  if (score >= 0.5) return "light-green";
  if (score >= 0.25) return "warning";
  return "error";
};

const getDaviesBouldinColor = (score) => {
  if (score === null || score === undefined) return "grey";
  if (score < 0.5) return "success";
  if (score < 1.0) return "light-green";
  if (score < 2.0) return "warning";
  return "error";
};

const getMetricTextColor = (level) => {
  const colors = {
    excellent: "text-success",
    good: "text-light-green",
    fair: "text-warning",
    poor: "text-error",
    info: "text-info",
  };
  return colors[level] || "text-grey";
};

const getMetricIcon = (level) => {
  const icons = {
    excellent: "mdi-check-circle",
    good: "mdi-check-circle-outline",
    fair: "mdi-alert-circle-outline",
    poor: "mdi-close-circle",
    info: "mdi-information",
  };
  return icons[level] || "mdi-information";
};

// Open document details from cluster list
const openDocumentDetails = (doc) => {
  selectedDocument.value = doc;
  showDetails.value = true;

  // Find neighbors from links
  const neighbors = links.value
    .filter((link) => link.source === doc.id || link.target === doc.id)
    .map((link) => {
      const neighborId = link.source === doc.id ? link.target : link.source;
      const neighbor = nodes.value.find((n) => n.id === neighborId);
      return neighbor ? { ...neighbor, similarity: link.similarity } : null;
    })
    .filter((n) => n !== null)
    .sort((a, b) => b.similarity - a.similarity)
    .slice(0, 10);

  selectedDocumentNeighbors.value = neighbors;
};

// Get edge color based on similarity - Elegant red gradient palette
const getEdgeColor = (similarity) => {
  if (similarity > 0.85) return "#7F1D1D"; // Deep Maroon - Very High
  if (similarity > 0.7) return "#991B1B"; // Dark Burgundy - High
  if (similarity > 0.55) return "#DC2626"; // Crimson Red - Medium-High
  if (similarity > 0.4) return "#EF4444"; // Bright Red - Medium
  if (similarity > 0.25) return "#F87171"; // Coral Red - Low-Medium
  return "#D6D3D1"; // Warm Gray - Low (stone-300)
};

// Get edge width based on similarity - more visible differences
const getEdgeWidth = (similarity) => {
  if (similarity > 0.85) return 4;
  if (similarity > 0.7) return 3;
  if (similarity > 0.55) return 2.5;
  if (similarity > 0.4) return 2;
  if (similarity > 0.25) return 1.5;
  return 1;
};

// Get edge opacity based on similarity - uniform when not hovered
const getEdgeOpacity = (similarity) => {
  return 0.25; // Uniform low opacity for all edges by default
};

// Get edge opacity when hovered/emphasized - show similarity differences
const getEdgeOpacityEmphasis = (similarity) => {
  if (similarity > 0.85) return 1.0;
  if (similarity > 0.7) return 0.9;
  if (similarity > 0.55) return 0.8;
  if (similarity > 0.4) return 0.7;
  if (similarity > 0.25) return 0.6;
  return 0.5;
};

// Get edge width when hovered - more visible differences
const getEdgeWidthEmphasis = (similarity) => {
  if (similarity > 0.85) return 8;
  if (similarity > 0.7) return 6;
  if (similarity > 0.55) return 5;
  if (similarity > 0.4) return 4;
  if (similarity > 0.25) return 3;
  return 2;
};

// Load clusters from API
const loadClusters = async () => {
  loading.value = true;
  try {
    const response = await axios.get("/api/documents/all_clusters/", {
      params: {
        include_edges: true,
        top_k: topK.value,
      },
    });

    nodes.value = response.data.nodes || [];
    links.value = response.data.links || [];
    clusterStats.value = response.data.cluster_stats || [];
    metadata.value = response.data.metadata || {};
    qualityMetrics.value = response.data.quality_metrics || null;

    console.log("✅ Clusters loaded:", {
      nodes: nodes.value.length,
      links: links.value.length,
      clusters: metadata.value.cluster_count,
      qualityMetrics: qualityMetrics.value,
    });

    loading.value = false;
    await nextTick();

    initChart();
  } catch (error) {
    console.error("❌ Error loading clusters:", error);
    loading.value = false;
  }
};

// ==================== SEMANTIC SEARCH FUNCTIONS ====================

// Execute semantic search by text query
const executeSearch = async () => {
  console.log("🔍 executeSearch called, query:", searchQuery.value);

  if (!searchQuery.value || !searchQuery.value.trim()) {
    console.log("⚠️ Empty query, returning");
    return;
  }

  searchLoading.value = true;
  searchResults.value = [];

  try {
    console.log("📤 Sending search request...");
    const response = await axios.post("/api/documents/semantic_search/", {
      query: searchQuery.value.trim(),
      top_n: searchTopN.value,
    });

    if (response.data && response.data.results) {
      // Map results to include id and similarity in consistent format
      searchResults.value = response.data.results.map((r) => ({
        id: r.document_id,
        title: r.title,
        similarity: r.similarity_score,
        cluster: r.cluster,
        case_number: r.case_number,
        legal_area: r.legal_area?.name || r.legal_area,
        ...r,
      }));

      // Update searchResultIds for quick lookup
      searchResultIds.value = new Set(searchResults.value.map((r) => r.id));

      console.log(
        `🔍 Search results: ${searchResults.value.length} documents found`
      );

      // Highlight results in chart
      highlightSearchResults();

      // Auto-zoom to primary cluster if results found
      if (dominantSearchCluster.value !== null) {
        zoomToCluster(dominantSearchCluster.value);
      }
    }
  } catch (error) {
    console.error("❌ Error in semantic search:", error);
  } finally {
    searchLoading.value = false;
  }
};

// Handle file upload for search
const handleFileUpload = (event) => {
  const file = event.target.files?.[0];
  if (file) {
    searchFile.value = file;
    executeSearchFromFile();
  }
};

// Trigger file input click
const triggerFileUpload = () => {
  fileInputRef.value?.click();
};

// Execute semantic search from uploaded file
const executeSearchFromFile = async () => {
  // In Vuetify 3, v-file-input returns an array
  const file = Array.isArray(searchFile.value)
    ? searchFile.value[0]
    : searchFile.value;

  if (!file) {
    console.log("⚠️ No file selected");
    return;
  }

  const fileName = file.name.toLowerCase();
  const isPdf = fileName.endsWith(".pdf");
  const isDoc = fileName.endsWith(".doc") || fileName.endsWith(".docx");

  // DOC/DOCX files are not supported
  if (isDoc) {
    console.warn("⚠️ DOC/DOCX files are not supported. Please use PDF or TXT.");
    alert("Los archivos DOC/DOCX no son soportados. Por favor usa PDF o TXT.");
    searchFile.value = null;
    return;
  }

  console.log("📄 Searching from file:", file.name, isPdf ? "(PDF)" : "(Text)");

  searchLoading.value = true;
  searchResults.value = [];

  try {
    let fileContent;

    if (isPdf) {
      // Read PDF content
      console.log("📑 Extracting text from PDF...");
      fileContent = await readPdfContent(file);
    } else {
      // Read text file content
      fileContent = await readFileContent(file);
    }

    if (!fileContent || !fileContent.trim()) {
      console.warn("⚠️ File is empty or could not be read");
      alert("El archivo está vacío o no se pudo extraer texto.");
      searchLoading.value = false;
      return;
    }

    console.log(`📝 Extracted ${fileContent.length} characters from file`);
    console.log(
      "📤 Sending file search request, content length:",
      fileContent.length
    );

    // Set query to file content preview
    searchQuery.value =
      fileContent.substring(0, 200) + (fileContent.length > 200 ? "..." : "");

    const response = await axios.post("/api/documents/semantic_search/", {
      query: fileContent,
      top_n: searchTopN.value,
    });

    if (response.data && response.data.results) {
      // Map results to include id and similarity in consistent format
      searchResults.value = response.data.results.map((r) => ({
        id: r.document_id,
        title: r.title,
        similarity: r.similarity_score,
        cluster: r.cluster,
        case_number: r.case_number,
        legal_area: r.legal_area?.name || r.legal_area,
        ...r,
      }));

      // Update searchResultIds for quick lookup
      searchResultIds.value = new Set(searchResults.value.map((r) => r.id));

      console.log(
        `🔍 File search results: ${searchResults.value.length} documents found`
      );

      // Highlight results in chart
      highlightSearchResults();

      // Auto-zoom to primary cluster if results found
      if (dominantSearchCluster.value !== null) {
        zoomToCluster(dominantSearchCluster.value);
      }
    }
  } catch (error) {
    console.error("❌ Error in file search:", error);
  } finally {
    searchLoading.value = false;
    // Reset file input
    if (fileInputRef.value) {
      fileInputRef.value.value = "";
    }
  }
};

// Read file content as text
const readFileContent = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => resolve(e.target.result);
    reader.onerror = (e) => reject(e);
    reader.readAsText(file);
  });
};

// Read PDF file content using pdf.js
const readPdfContent = async (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();

    reader.onload = async (e) => {
      try {
        const typedArray = new Uint8Array(e.target.result);

        // Load the PDF document
        const pdf = await pdfjsLib.getDocument({ data: typedArray }).promise;

        console.log(`📑 PDF loaded: ${pdf.numPages} pages`);

        let fullText = "";

        // Extract text from each page
        for (let pageNum = 1; pageNum <= pdf.numPages; pageNum++) {
          const page = await pdf.getPage(pageNum);
          const textContent = await page.getTextContent();

          // Combine text items
          const pageText = textContent.items.map((item) => item.str).join(" ");

          fullText += pageText + "\n\n";

          // Log progress for large PDFs
          if (pdf.numPages > 10 && pageNum % 10 === 0) {
            console.log(`📄 Processed ${pageNum}/${pdf.numPages} pages...`);
          }
        }

        // Clean up the text
        fullText = fullText
          .replace(/\s+/g, " ") // Normalize whitespace
          .replace(/\n\s*\n/g, "\n\n") // Normalize paragraph breaks
          .trim();

        console.log(`✅ PDF text extracted: ${fullText.length} characters`);
        resolve(fullText);
      } catch (error) {
        console.error("❌ Error parsing PDF:", error);
        reject(error);
      }
    };

    reader.onerror = (e) => {
      console.error("❌ Error reading file:", e);
      reject(e);
    };

    reader.readAsArrayBuffer(file);
  });
};

// Clear search results
const clearSearch = () => {
  searchQuery.value = "";
  searchResults.value = [];
  searchResultIds.value = new Set();
  searchFile.value = null;
  if (fileInputRef.value) {
    fileInputRef.value.value = "";
  }

  // Rebuild and UPDATE chart without search highlighting
  if (chartInstance) {
    updateChart();
  }
};

// Highlight search results in chart
const highlightSearchResults = () => {
  if (!hasSearchResults.value) {
    console.log("⚠️ No search results to highlight");
    return;
  }

  // Rebuild and UPDATE chart with search highlighting
  updateChart();

  console.log(
    `✨ Highlighted ${searchResults.value.length} search results in chart`
  );
};

// Zoom to a specific cluster
const zoomToCluster = (clusterId) => {
  if (!chartInstance) return;

  // Find nodes in the cluster
  const clusterNodes = nodes.value.filter((node) => node.cluster === clusterId);

  if (clusterNodes.length === 0) return;

  // Calculate bounding box for the cluster
  let minX = Infinity,
    maxX = -Infinity;
  let minY = Infinity,
    maxY = -Infinity;

  clusterNodes.forEach((node) => {
    minX = Math.min(minX, node.x);
    maxX = Math.max(maxX, node.x);
    minY = Math.min(minY, node.y);
    maxY = Math.max(maxY, node.y);
  });

  // Add padding
  const padding = 0.2;
  const rangeX = maxX - minX || 1;
  const rangeY = maxY - minY || 1;
  minX -= rangeX * padding;
  maxX += rangeX * padding;
  minY -= rangeY * padding;
  maxY += rangeY * padding;

  // Apply zoom using dataZoom
  chartInstance.dispatchAction({
    type: "dataZoom",
    dataZoomIndex: [0, 1],
    start: 0,
    end: 100,
  });

  // Use a slight delay to ensure the chart is ready
  setTimeout(() => {
    chartInstance.dispatchAction({
      type: "dataZoom",
      dataZoomIndex: 0,
      startValue: minX,
      endValue: maxX,
    });
    chartInstance.dispatchAction({
      type: "dataZoom",
      dataZoomIndex: 1,
      startValue: minY,
      endValue: maxY,
    });
  }, 100);

  console.log(`🔎 Zoomed to cluster ${clusterId}`);
};

// Alias functions for template compatibility
const performSearch = executeSearch;
const performFileSearch = executeSearchFromFile;

// Handle file selection
const onFileSelected = (file) => {
  if (file) {
    searchFile.value = file;
  }
};

// Open search result document in detail panel
const openSearchResult = (result) => {
  if (result && result.id) {
    // Find node by document_id
    const node = nodes.value.find((n) => n.id === result.id);
    if (node) {
      openDocumentDetails(node);
    } else {
      // If node not found, use result data
      const nodeFromResult = {
        id: result.id,
        title: result.title,
        cluster: result.cluster,
        case_number: result.case_number,
        legal_area: result.legal_area,
        ...result,
      };
      openDocumentDetails(nodeFromResult);
    }
  }
};

// Get color based on search similarity score
const getSearchResultColor = (similarity) => {
  if (similarity >= 0.8) return "#FF4500"; // OrangeRed for very high
  if (similarity >= 0.6) return "#FF8C00"; // DarkOrange
  if (similarity >= 0.4) return "#FFA500"; // Orange
  if (similarity >= 0.2) return "#FFD700"; // Gold
  return "#DAA520"; // GoldenRod for low
};

// ==================== END SEMANTIC SEARCH FUNCTIONS ====================

// Regenerate clusters
const regenerateClusters = async () => {
  regenerating.value = true;
  regenerationProgress.value = {
    message: "Iniciando regeneración de clusters...",
    details: null,
    completed: false,
  };

  try {
    console.log("🔄 Triggering cluster regeneration...");
    const response = await axios.post("/api/documents/regenerate_clusters/", {
      max_documents: 1000,
      use_enhanced_embedding: true,
      algorithm: "hdbscan",
    });

    const { task_id, estimated_time_seconds, document_count, message } =
      response.data;

    regenerationProgress.value = {
      message: "Regenerando clusters...",
      details: `Procesando ${document_count} documentos. Tiempo estimado: ${estimated_time_seconds}s`,
      completed: false,
    };

    const waitTime = (estimated_time_seconds + 2) * 1000;
    await new Promise((resolve) => setTimeout(resolve, waitTime));

    regenerationProgress.value = {
      message: "Cargando nuevos clusters...",
      details: null,
      completed: false,
    };

    await loadClusters();

    regenerationProgress.value = {
      message: "✅ Clusters regenerados exitosamente",
      details: `${document_count} documentos procesados`,
      completed: true,
    };

    setTimeout(() => {
      regenerationProgress.value = null;
    }, 5000);
  } catch (error) {
    console.error("❌ Error regenerating clusters:", error);
    regenerationProgress.value = {
      message: "❌ Error al regenerar clusters",
      details:
        error.response?.data?.error || error.message || "Error desconocido",
      completed: true,
    };
    setTimeout(() => {
      regenerationProgress.value = null;
    }, 10000);
  } finally {
    regenerating.value = false;
  }
};

// Handle top-k change
const onTopKChange = async () => {
  const currentCluster = selectedCluster.value;

  try {
    const response = await axios.get("/api/documents/all_clusters/", {
      params: {
        include_edges: true,
        top_k: topK.value,
      },
    });

    nodes.value = response.data.nodes || [];
    links.value = response.data.links || [];
    clusterStats.value = response.data.cluster_stats || [];
    metadata.value = response.data.metadata || {};

    if (currentCluster !== null) {
      selectedCluster.value = currentCluster;
    }

    updateChart();
  } catch (error) {
    console.error("❌ Error updating top-k:", error);
  }
};

// Compute filtered data
const filteredNodes = computed(() => {
  if (selectedCluster.value === null) {
    return nodes.value;
  }
  return nodes.value.filter((n) => n.cluster === selectedCluster.value);
});

const filteredLinks = computed(() => {
  const nodeIds = new Set(filteredNodes.value.map((n) => n.id));
  return links.value.filter((l) => {
    const sourceId = typeof l.source === "object" ? l.source.id : l.source;
    const targetId = typeof l.target === "object" ? l.target.id : l.target;
    return nodeIds.has(sourceId) && nodeIds.has(targetId);
  });
});

// Get documents belonging to selected cluster (sorted by title)
const selectedClusterDocuments = computed(() => {
  if (selectedCluster.value === null) return [];
  return nodes.value
    .filter((n) => n.cluster === selectedCluster.value)
    .sort((a, b) => (a.title || "").localeCompare(b.title || ""));
});

// Get stats for selected cluster
const selectedClusterStats = computed(() => {
  if (selectedCluster.value === null) return null;
  return clusterStats.value.find(
    (s) => s.cluster_label === selectedCluster.value
  );
});

// Search Results: Find which cluster has most search results
const dominantSearchCluster = computed(() => {
  if (searchResults.value.length === 0) return null;

  // Count results per cluster
  const clusterCounts = {};
  searchResults.value.forEach((result) => {
    const cluster = result.cluster;
    clusterCounts[cluster] = (clusterCounts[cluster] || 0) + 1;
  });

  // Find cluster with max count
  let maxCluster = null;
  let maxCount = 0;
  for (const [cluster, count] of Object.entries(clusterCounts)) {
    if (count > maxCount) {
      maxCount = count;
      maxCluster = parseInt(cluster);
    }
  }
  return maxCluster;
});

const dominantSearchClusterCount = computed(() => {
  if (dominantSearchCluster.value === null) return 0;
  return searchResults.value.filter(
    (r) => r.cluster === dominantSearchCluster.value
  ).length;
});

// Map of document ID -> similarity score for quick lookup in chart building
const searchResultsMap = computed(() => {
  const map = new Map();
  searchResults.value.forEach((result) => {
    map.set(result.id, result.similarity);
  });
  return map;
});

// Check if we have active search results
const hasSearchResults = computed(() => searchResults.value.length > 0);

// Get similarity score for a node ID (from search results)
const getNodeSearchSimilarity = (nodeId) => {
  const result = searchResults.value.find((r) => r.id === nodeId);
  return result ? result.similarity : null;
};

// Initialize ECharts
const initChart = () => {
  if (!chartContainer.value) {
    console.warn("⚠️ Chart container not ready");
    return;
  }

  // Dispose existing instance
  if (chartInstance) {
    chartInstance.dispose();
  }

  chartInstance = echarts.init(chartContainer.value, null, {
    renderer: "canvas",
  });

  // Set up event handlers
  chartInstance.on("click", "series.graph", handleNodeClick);
  chartInstance.on("mouseover", "series.graph", handleNodeHover);
  chartInstance.on("mouseout", "series.graph", handleNodeMouseOut);

  updateChart();
  console.log("✅ ECharts initialized");
};

// Build chart option
const buildChartOption = () => {
  // Safety check for empty data
  if (filteredNodes.value.length === 0) {
    return {
      series: [],
    };
  }

  // Calculate bounds for centering
  const xValues = filteredNodes.value.map((n) => n.x);
  const yValues = filteredNodes.value.map((n) => n.y);
  const minX = Math.min(...xValues);
  const maxX = Math.max(...xValues);
  const minY = Math.min(...yValues);
  const maxY = Math.max(...yValues);
  const rangeX = maxX - minX || 1;
  const rangeY = maxY - minY || 1;

  // Normalize positions to fit in chart area
  const padding = 80;
  const chartWidth = chartContainer.value?.clientWidth || 800;
  const chartHeight = chartContainer.value?.clientHeight || 700;
  const scaleX = (chartWidth - padding * 2) / rangeX;
  const scaleY = (chartHeight - padding * 2) / rangeY;
  const scale = Math.min(scaleX, scaleY);

  // When viewing single cluster, expand nodes more aggressively
  let expansionFactor = 1.0;
  if (selectedCluster.value !== null) {
    const nodeCount = filteredNodes.value.length;
    if (nodeCount <= 5) expansionFactor = 4.0;
    else if (nodeCount <= 10) expansionFactor = 3.0;
    else if (nodeCount <= 20) expansionFactor = 2.5;
    else if (nodeCount <= 35) expansionFactor = 2.0;
    else expansionFactor = 1.5;
  }

  // Center of filtered data
  const centerX = (minX + maxX) / 2;
  const centerY = (minY + maxY) / 2;

  // Build categories first - map cluster values to indices
  const uniqueClusters = [
    ...new Set(filteredNodes.value.map((n) => n.cluster)),
  ].sort((a, b) => a - b);
  const clusterToIndex = new Map();
  const categories = uniqueClusters.map((cluster, index) => {
    clusterToIndex.set(cluster, index);
    return {
      name: cluster === -1 ? "Ruido" : `Cluster ${cluster}`,
      itemStyle: {
        color: getClusterColor(cluster),
      },
    };
  });

  // Transform nodes for ECharts
  const graphNodes = filteredNodes.value.map((node) => {
    // Expand from center
    const expandedX = centerX + (node.x - centerX) * expansionFactor;
    const expandedY = centerY + (node.y - centerY) * expansionFactor;

    // Normalize to chart coordinates
    const normalizedX =
      ((expandedX - minX) / rangeX) * (chartWidth - padding * 2) + padding;
    const normalizedY =
      ((expandedY - minY) / rangeY) * (chartHeight - padding * 2) + padding;

    // Get the category index for this cluster
    const categoryIndex = clusterToIndex.get(node.cluster) ?? 0;

    // Check if this document is in search results
    const searchSimilarity = searchResultsMap.value.get(node.id);
    const isSearchResult = searchSimilarity !== undefined;

    // Calculate search-based styling
    let nodeColor = getClusterColor(node.cluster);
    let nodeBorderColor = "#ffffff";
    let nodeBorderWidth = 2;
    let nodeShadowBlur = 8;
    let nodeShadowColor = "rgba(0, 0, 0, 0.25)";
    let nodeSymbolSize = node.is_noise ? 12 : 18;
    let nodeSymbol = "circle";

    if (isSearchResult) {
      // Highlight search results with gold/orange gradient based on similarity
      const intensity = Math.min(1, searchSimilarity * 1.5); // Boost visibility

      // Gold to orange gradient based on similarity
      const r = Math.round(255);
      const g = Math.round(215 - intensity * 100); // 215 -> 115
      const b = Math.round(0);
      nodeColor = `rgb(${r}, ${g}, ${b})`;

      // Enhanced border for search results
      nodeBorderColor = "#FF4500"; // OrangeRed
      nodeBorderWidth = 3;
      nodeShadowBlur = 15;
      nodeShadowColor = "rgba(255, 165, 0, 0.6)"; // Orange glow

      // Larger size for search results (scale with similarity)
      nodeSymbolSize = 24 + intensity * 12; // 24-36
      nodeSymbol = "diamond"; // Different shape for search results
    } else if (hasSearchResults.value) {
      // Dim non-matching documents when search is active
      nodeColor = nodeColor + "80"; // Add transparency
      nodeShadowBlur = 4;
    }

    return {
      id: String(node.id),
      name: node.title || `Doc ${node.id}`,
      x: useForceLayout.value ? undefined : normalizedX,
      y: useForceLayout.value ? undefined : normalizedY,
      value: [normalizedX, normalizedY],
      symbol: nodeSymbol,
      symbolSize: nodeSymbolSize,
      category: categoryIndex, // Use index, not raw cluster value
      itemStyle: {
        color: nodeColor,
        borderColor: nodeBorderColor,
        borderWidth: nodeBorderWidth,
        shadowBlur: nodeShadowBlur,
        shadowColor: nodeShadowColor,
      },
      label: {
        show: isSearchResult, // Show labels for search results
        formatter: isSearchResult
          ? `{similarity|${(searchSimilarity * 100).toFixed(0)}%}`
          : undefined,
        position: "top",
        distance: 5,
        rich: {
          similarity: {
            fontSize: 10,
            fontWeight: "bold",
            color: "#FF4500",
            backgroundColor: "rgba(255, 255, 255, 0.9)",
            padding: [2, 4],
            borderRadius: 3,
          },
        },
      },
      emphasis: {
        scale: 1.5,
        focus: "adjacency",
        label: {
          show: true,
          formatter: (params) => {
            const title = params.data.name || "";
            const simLabel = params.data.searchSimilarity
              ? ` (${(params.data.searchSimilarity * 100).toFixed(0)}% similar)`
              : "";
            const fullTitle = title + simLabel;
            return fullTitle.length > 35
              ? fullTitle.substring(0, 35) + "..."
              : fullTitle;
          },
          position: "top",
          fontSize: 11,
          fontWeight: "bold",
          color: "#1F2937",
          backgroundColor: "rgba(255, 255, 255, 0.95)",
          padding: [6, 10],
          borderRadius: 6,
          borderColor: "#E5E7EB",
          borderWidth: 1,
        },
      },
      // Store original data for click handler
      originalData: node,
      // Store search similarity if available
      searchSimilarity: searchSimilarity || null,
    };
  });

  // Create a set of valid node IDs for link validation
  const validNodeIds = new Set(graphNodes.map((n) => n.id));

  // Transform links for ECharts with better styling
  const graphLinks = showEdges.value
    ? filteredLinks.value
        .map((link) => {
          const sourceId = String(
            typeof link.source === "object" ? link.source.id : link.source
          );
          const targetId = String(
            typeof link.target === "object" ? link.target.id : link.target
          );
          const similarity = link.similarity || 0.5;

          // Only include links where both nodes exist
          if (!validNodeIds.has(sourceId) || !validNodeIds.has(targetId)) {
            return null;
          }

          return {
            source: sourceId,
            target: targetId,
            value: similarity,
            lineStyle: {
              color: getEdgeColor(similarity),
              width: 1.5, // Uniform width when not hovered
              opacity: 0.15, // Uniform low opacity when not hovered
              curveness: 0.15, // Slight curve to avoid overlap
              cap: "round",
              join: "round",
            },
            emphasis: {
              lineStyle: {
                color: getEdgeColor(similarity),
                width: getEdgeWidthEmphasis(similarity), // Show width differences on hover
                opacity: getEdgeOpacityEmphasis(similarity), // Show opacity differences on hover
                shadowBlur: 10,
                shadowColor: getEdgeColor(similarity),
              },
            },
          };
        })
        .filter((link) => link !== null)
    : [];

  console.log("📊 Building chart:", {
    nodes: graphNodes.length,
    links: graphLinks.length,
    categories: categories.length,
    selectedCluster: selectedCluster.value,
    clusterMapping: Object.fromEntries(clusterToIndex),
  });

  return {
    tooltip: {
      trigger: "item",
      enterable: true,
      confine: true,
      formatter: (params) => {
        if (params.dataType === "node") {
          const data = params.data.originalData || {};
          const clusterColor = getClusterColor(data.cluster);
          return `
            <div style="padding: 10px; min-width: 200px;">
              <div style="font-weight: bold; font-size: 14px; margin-bottom: 8px; color: #1F2937;">
                ${data.title || "Documento"}
              </div>
              <div style="display: flex; align-items: center; margin-bottom: 6px;">
                <span style="display: inline-block; width: 12px; height: 12px; border-radius: 50%; background: ${clusterColor}; margin-right: 8px;"></span>
                <span>Cluster ${
                  data.cluster === -1 ? "(Ruido)" : data.cluster
                }</span>
              </div>
              ${
                data.case_number
                  ? `<div style="color: #6B7280; margin-bottom: 4px;">📁 ${data.case_number}</div>`
                  : ""
              }
              ${
                data.legal_area
                  ? `<div style="color: #6B7280;">⚖️ ${data.legal_area}</div>`
                  : ""
              }
            </div>
          `;
        } else if (params.dataType === "edge") {
          const similarity = params.data.value || 0;
          const percent = (similarity * 100).toFixed(1);
          const color = getEdgeColor(similarity);
          return `
            <div style="padding: 8px;">
              <div style="font-weight: bold; margin-bottom: 4px;">Conexión</div>
              <div style="display: flex; align-items: center;">
                <span style="display: inline-block; width: 30px; height: 4px; background: ${color}; border-radius: 2px; margin-right: 8px;"></span>
                <span>Similitud: ${percent}%</span>
              </div>
            </div>
          `;
        }
        return "";
      },
      backgroundColor: "rgba(255, 255, 255, 0.98)",
      borderColor: "#E5E7EB",
      borderWidth: 1,
      borderRadius: 8,
      textStyle: {
        color: "#374151",
        fontSize: 13,
      },
      extraCssText: "box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);",
    },
    legend: {
      show: false,
    },
    animationDuration: 600,
    animationEasingUpdate: "cubicInOut",
    series: [
      {
        type: "graph",
        layout: useForceLayout.value ? "force" : "none",
        data: graphNodes,
        links: graphLinks,
        categories: categories,
        roam: true,
        draggable: true,
        edgeSymbol: ["none", "none"],
        cursor: "pointer",
        force: useForceLayout.value
          ? {
              repulsion: 250,
              gravity: 0.08,
              edgeLength: [100, 250],
              friction: 0.5,
              layoutAnimation: true,
            }
          : undefined,
        scaleLimit: {
          min: 0.1,
          max: 10,
        },
        lineStyle: {
          curveness: 0.15,
          cap: "round",
        },
        emphasis: {
          focus: "adjacency",
          lineStyle: {
            width: 5,
          },
          itemStyle: {
            borderWidth: 3,
            borderColor: "#1F2937",
          },
        },
        blur: {
          itemStyle: {
            opacity: 0.15,
          },
          lineStyle: {
            opacity: 0.05,
          },
        },
      },
    ],
  };
};

// Update chart with current data
const updateChart = () => {
  if (!chartInstance) {
    console.warn("⚠️ Chart instance not ready");
    return;
  }

  const option = buildChartOption();
  chartInstance.setOption(option, {
    notMerge: true,
    lazyUpdate: true,
  });

  console.log("✅ Chart updated:", {
    nodes: filteredNodes.value.length,
    links: showEdges.value ? filteredLinks.value.length : 0,
    mode: useForceLayout.value ? "FORCE" : "FIXED",
  });
};

// Event handlers
const handleNodeClick = (params) => {
  if (params.dataType === "node" && params.data.originalData) {
    const nodeData = params.data.originalData;
    const fullNode = nodes.value.find((n) => n.id === nodeData.id);

    if (fullNode) {
      selectedDocument.value = fullNode;
      showDetails.value = true;

      // Find neighbors from links
      const neighbors = links.value
        .filter(
          (link) => link.source === fullNode.id || link.target === fullNode.id
        )
        .map((link) => {
          const neighborId =
            link.source === fullNode.id ? link.target : link.source;
          const neighbor = nodes.value.find((n) => n.id === neighborId);
          return neighbor ? { ...neighbor, similarity: link.similarity } : null;
        })
        .filter((n) => n !== null)
        .sort((a, b) => b.similarity - a.similarity)
        .slice(0, 10);

      selectedDocumentNeighbors.value = neighbors;
      console.log(
        `✅ Found ${neighbors.length} neighbors for document ${fullNode.id}`
      );
    }
  }
};

const handleNodeHover = (params) => {
  if (params.dataType !== "node" || !chartInstance) return;

  const nodeId = params.data.id;

  // Find all links connected to this node and update their styles
  const option = chartInstance.getOption();
  if (!option.series || !option.series[0] || !option.series[0].links) return;

  const updatedLinks = option.series[0].links.map((link) => {
    const isConnected = link.source === nodeId || link.target === nodeId;
    const similarity = link.value || 0.5;

    if (isConnected) {
      // Highlight connected edges with similarity-based styling
      return {
        ...link,
        lineStyle: {
          ...link.lineStyle,
          color: getEdgeColor(similarity),
          width: getEdgeWidthEmphasis(similarity),
          opacity: getEdgeOpacityEmphasis(similarity),
          shadowBlur: 12,
          shadowColor: getEdgeColor(similarity),
        },
      };
    } else {
      // Dim non-connected edges
      return {
        ...link,
        lineStyle: {
          ...link.lineStyle,
          color: getEdgeColor(similarity),
          width: 1,
          opacity: 0.15,
          shadowBlur: 0,
          shadowColor: "transparent",
        },
      };
    }
  });

  chartInstance.setOption({
    series: [
      {
        links: updatedLinks,
      },
    ],
  });
};

const handleNodeMouseOut = (params) => {
  if (!chartInstance) return;

  // Reset all edges to default uniform style
  const option = chartInstance.getOption();
  if (!option.series || !option.series[0] || !option.series[0].links) return;

  const resetLinks = option.series[0].links.map((link) => {
    const similarity = link.value || 0.5;
    return {
      ...link,
      lineStyle: {
        color: getEdgeColor(similarity),
        width: 1.5,
        opacity: 0.15,
        curveness: 0.15,
        cap: "round",
        join: "round",
        shadowBlur: 0,
        shadowColor: "transparent",
      },
    };
  });

  chartInstance.setOption({
    series: [
      {
        links: resetLinks,
      },
    ],
  });
};

// Filter by cluster
const filterByCluster = (clusterLabel) => {
  if (selectedCluster.value === clusterLabel) {
    clearFilter();
  } else {
    selectedCluster.value = clusterLabel;
    updateChart();

    // Center on cluster after a short delay
    setTimeout(() => {
      if (chartInstance) {
        chartInstance.dispatchAction({
          type: "restore",
        });
      }
    }, 300);
  }
};

const clearFilter = () => {
  selectedCluster.value = null;
  updateChart();
};

// Highlight node in graph when hovering document in list
// Replicates the same behavior as handleNodeHover for consistency
const highlightNodeInGraph = (nodeId) => {
  if (!chartInstance) return;

  const nodeIdStr = String(nodeId);

  // Dispatch highlight action to ECharts for node emphasis
  const nodeIndex = filteredNodes.value.findIndex((n) => n.id === nodeId);
  if (nodeIndex !== -1) {
    chartInstance.dispatchAction({
      type: "highlight",
      seriesIndex: 0,
      dataIndex: nodeIndex,
    });

    // Show tooltip
    chartInstance.dispatchAction({
      type: "showTip",
      seriesIndex: 0,
      dataIndex: nodeIndex,
    });
  }

  // Update edges with same logic as handleNodeHover
  const option = chartInstance.getOption();
  if (!option.series || !option.series[0] || !option.series[0].links) return;

  const updatedLinks = option.series[0].links.map((link) => {
    const isConnected = link.source === nodeIdStr || link.target === nodeIdStr;
    const similarity = link.value || 0.5;

    if (isConnected) {
      // Highlight connected edges with similarity-based styling
      return {
        ...link,
        lineStyle: {
          ...link.lineStyle,
          color: getEdgeColor(similarity),
          width: getEdgeWidthEmphasis(similarity),
          opacity: getEdgeOpacityEmphasis(similarity),
          shadowBlur: 12,
          shadowColor: getEdgeColor(similarity),
        },
      };
    } else {
      // Dim non-connected edges
      return {
        ...link,
        lineStyle: {
          ...link.lineStyle,
          color: getEdgeColor(similarity),
          width: 1,
          opacity: 0.05,
          shadowBlur: 0,
          shadowColor: "transparent",
        },
      };
    }
  });

  chartInstance.setOption({
    series: [
      {
        links: updatedLinks,
      },
    ],
  });
};

const unhighlightNodeInGraph = () => {
  if (!chartInstance) return;

  // Remove highlight
  chartInstance.dispatchAction({
    type: "downplay",
    seriesIndex: 0,
  });

  // Hide tooltip
  chartInstance.dispatchAction({
    type: "hideTip",
  });

  // Reset all edges to default uniform style (same as handleNodeMouseOut)
  const option = chartInstance.getOption();
  if (!option.series || !option.series[0] || !option.series[0].links) return;

  const resetLinks = option.series[0].links.map((link) => {
    const similarity = link.value || 0.5;
    return {
      ...link,
      lineStyle: {
        color: getEdgeColor(similarity),
        width: 1.5,
        opacity: 0.15,
        curveness: 0.15,
        cap: "round",
        join: "round",
        shadowBlur: 0,
        shadowColor: "transparent",
      },
    };
  });

  chartInstance.setOption({
    series: [
      {
        links: resetLinks,
      },
    ],
  });
};

// Aliases for template compatibility with search results
const highlightNodeInChart = highlightNodeInGraph;
const clearNodeHighlight = unhighlightNodeInGraph;

// Zoom controls
const zoomIn = () => {
  if (!chartInstance) return;
  const option = chartInstance.getOption();
  if (option.series && option.series[0]) {
    const currentZoom = option.series[0].zoom || 1;
    chartInstance.setOption({
      series: [
        {
          zoom: currentZoom * 1.3,
        },
      ],
    });
  }
};

const zoomOut = () => {
  if (!chartInstance) return;
  const option = chartInstance.getOption();
  if (option.series && option.series[0]) {
    const currentZoom = option.series[0].zoom || 1;
    chartInstance.setOption({
      series: [
        {
          zoom: currentZoom / 1.3,
        },
      ],
    });
  }
};

const fitToView = () => {
  if (!chartInstance) return;
  chartInstance.dispatchAction({
    type: "restore",
  });
};

// Watch for changes
watch(showEdges, () => {
  updateChart();
});

watch(useForceLayout, () => {
  updateChart();
});

// Format date
const formatDate = (dateString) => {
  if (!dateString) return "N/A";
  const date = new Date(dateString);
  return date.toLocaleDateString("es-ES", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
};

// Navigate to document chat/analysis view (opens in new tab to preserve state)
const openDocumentChat = (doc) => {
  if (!doc || !doc.id) {
    console.warn("No document ID available");
    return;
  }

  // Open in new tab to preserve current view state
  const url = `/document/${doc.id}`;
  window.open(url, "_blank");
};

// Lifecycle
onMounted(async () => {
  await loadClusters();

  // Setup resize observer
  await nextTick();
  if (chartContainer.value) {
    resizeObserver = new ResizeObserver(() => {
      if (chartInstance) {
        chartInstance.resize();
      }
    });
    resizeObserver.observe(chartContainer.value);
    console.log("✅ ResizeObserver attached");
  }
});

onUnmounted(() => {
  if (chartInstance) {
    chartInstance.dispose();
    chartInstance = null;
  }
  if (resizeObserver) {
    resizeObserver.disconnect();
  }
});
</script>

<style scoped>
.clusters-view-echarts {
  min-height: calc(100vh - 64px);
}

.gap-2 {
  gap: 8px;
}

.gap-3 {
  gap: 12px;
}

.chart-container {
  overflow: hidden;
  position: relative;
  background: linear-gradient(135deg, #fafafa 0%, #f5f5f5 100%);
}

.graph-card {
  height: 100%;
}

.sidebar-card {
  overflow: hidden;
}

/* Cluster list section with scroll */
.cluster-list-section {
  overflow-y: auto;
  transition: max-height 0.3s ease;
}

/* Documents list section */
.documents-list-section {
  overflow: hidden;
}

.cluster-list-item {
  cursor: pointer;
  transition: all 0.2s ease;
  border-left: 3px solid transparent;
}

.cluster-list-item:hover {
  background-color: rgba(25, 118, 210, 0.08);
}

.selected-cluster-item {
  background-color: rgba(25, 118, 210, 0.12) !important;
  border-left: 3px solid #1976d2 !important;
}

.cluster-doc-item {
  cursor: pointer;
  transition: background-color 0.2s;
}

.cluster-doc-item:hover {
  background-color: rgba(25, 118, 210, 0.08) !important;
}

.metric-item {
  padding: 4px 12px;
  border-radius: 8px;
  transition: background-color 0.2s;
}

.metric-item:hover {
  background-color: rgba(0, 0, 0, 0.04);
}

.gap-1 {
  gap: 4px;
}

/* Compact switch styling */
.compact-switch {
  transform: scale(0.9);
}

/* Fill height utility */
.fill-height {
  height: 100%;
}

/* Custom scrollbar for sidebar */
.cluster-list-section::-webkit-scrollbar,
.documents-list-section::-webkit-scrollbar {
  width: 6px;
}

.cluster-list-section::-webkit-scrollbar-track,
.documents-list-section::-webkit-scrollbar-track {
  background: #f1f1f1;
}

.cluster-list-section::-webkit-scrollbar-thumb,
.documents-list-section::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.cluster-list-section::-webkit-scrollbar-thumb:hover,
.documents-list-section::-webkit-scrollbar-thumb:hover {
  background: #a1a1a1;
}

/* Search Results Styling */
.search-results-section {
  overflow-y: auto;
}

.search-results-section::-webkit-scrollbar {
  width: 6px;
}

.search-results-section::-webkit-scrollbar-track {
  background: #f1f1f1;
}

.search-results-section::-webkit-scrollbar-thumb {
  background: #ffb300;
  border-radius: 3px;
}

.search-results-section::-webkit-scrollbar-thumb:hover {
  background: #ff8f00;
}

.search-result-item {
  cursor: pointer;
  transition: background-color 0.2s, transform 0.1s;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.search-result-item:hover {
  background-color: rgba(255, 193, 7, 0.15) !important;
  transform: translateX(2px);
}

.search-result-item:last-child {
  border-bottom: none;
}

/* Search highlight animation for chart nodes */
@keyframes pulse-highlight {
  0% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.2);
    opacity: 0.8;
  }
  100% {
    transform: scale(1);
    opacity: 1;
  }
}
</style>
