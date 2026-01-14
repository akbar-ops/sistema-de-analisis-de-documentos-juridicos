<template>
  <v-container
    fluid
    class="clusters-view pa-6"
    style="max-height: calc(100vh - 64px); overflow-y: auto"
  >
    <!-- Header -->
    <v-row>
      <v-col cols="12">
        <div class="d-flex align-center justify-space-between mb-4">
          <div>
            <h1 class="text-h4 font-weight-bold mb-2">
              <v-icon size="large" class="mr-2">mdi-chart-bubble</v-icon>
              Explorador de Clusters
            </h1>
            <p class="text-subtitle-1 text-grey">
              Visualiza agrupaciones de documentos similares mediante algoritmos
              de clustering
            </p>
          </div>
          <div class="d-flex gap-2">
            <v-btn
              v-if="selectedCluster !== null"
              color="secondary"
              prepend-icon="mdi-target"
              @click="centerGraph"
              variant="tonal"
              size="large"
            >
              Centrar Grafo
            </v-btn>
            <v-btn
              color="primary"
              prepend-icon="mdi-refresh"
              @click="loadClusters"
              :loading="loading"
              size="large"
            >
              Actualizar
            </v-btn>
          </div>
        </div>
      </v-col>
    </v-row>

    <!-- Configuration Panel -->
    <v-row>
      <v-col cols="12">
        <v-card elevation="2">
          <v-card-title class="bg-grey-lighten-3">
            <v-icon class="mr-2">mdi-tune</v-icon>
            Configuración del Clustering
          </v-card-title>
          <v-card-text>
            <v-row align="center">
              <!-- Algorithm Selection -->
              <v-col cols="12" md="3">
                <v-select
                  v-model="params.algorithm"
                  label="Algoritmo"
                  :items="algorithmOptions"
                  item-title="label"
                  item-value="value"
                  variant="outlined"
                  density="comfortable"
                  prepend-icon="mdi-brain"
                  hint="Selecciona el algoritmo de clustering"
                  persistent-hint
                >
                  <template #item="{ props, item }">
                    <v-list-item v-bind="props">
                      <template #subtitle>
                        <span class="text-caption">{{
                          item.raw.description
                        }}</span>
                      </template>
                    </v-list-item>
                  </template>
                </v-select>
              </v-col>

              <!-- Metric Selection -->
              <v-col cols="12" md="3">
                <v-select
                  v-model="params.metric"
                  label="Métrica de Distancia"
                  :items="metricOptions"
                  item-title="label"
                  item-value="value"
                  variant="outlined"
                  density="comfortable"
                  prepend-icon="mdi-ruler"
                  hint="Método para calcular similitud"
                  persistent-hint
                ></v-select>
              </v-col>

              <!-- Number of Clusters (for K-Means/Agglomerative) -->
              <v-col cols="12" md="3">
                <v-text-field
                  v-model.number="params.nClusters"
                  label="Número de Clusters"
                  type="number"
                  :min="2"
                  :max="20"
                  variant="outlined"
                  density="comfortable"
                  prepend-icon="mdi-numeric"
                  :disabled="
                    !['kmeans', 'agglomerative'].includes(params.algorithm)
                  "
                  hint="Para K-Means y Agglomerative"
                  persistent-hint
                ></v-text-field>
              </v-col>

              <!-- Max Documents -->
              <v-col cols="12" md="3">
                <v-text-field
                  v-model.number="params.maxDocuments"
                  label="Máx. Documentos"
                  type="number"
                  :min="10"
                  :max="1000"
                  :step="10"
                  variant="outlined"
                  density="comfortable"
                  prepend-icon="mdi-file-document-multiple"
                  hint="Limitar para mejor rendimiento"
                  persistent-hint
                ></v-text-field>
              </v-col>

              <!-- Embedding Type -->
              <v-col cols="12" md="3">
                <v-select
                  v-model="params.useEnhancedEmbedding"
                  label="Tipo de Embedding"
                  :items="embeddingOptions"
                  item-title="label"
                  item-value="value"
                  variant="outlined"
                  density="comfortable"
                  prepend-icon="mdi-vector-triangle"
                  hint="Seleccionar tipo de embedding"
                  persistent-hint
                ></v-select>
              </v-col>
            </v-row>

            <!-- Advanced Parameters (Collapsible) -->
            <v-expansion-panels variant="accordion" class="mt-4">
              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon class="mr-2">mdi-tune-vertical</v-icon>
                  Parámetros Avanzados
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <v-row>
                    <!-- Epsilon (DBSCAN) -->
                    <v-col cols="12" md="4">
                      <v-slider
                        v-model="params.eps"
                        label="Epsilon (eps)"
                        :min="0.001"
                        :max="0.5"
                        :step="0.001"
                        thumb-label
                        :disabled="params.algorithm !== 'dbscan'"
                      >
                        <template #append>
                          <v-chip size="small" color="primary">
                            {{ params.eps.toFixed(3) }}
                          </v-chip>
                        </template>
                      </v-slider>
                      <div class="text-caption text-grey">
                        Distancia máxima entre puntos (DBSCAN)
                      </div>
                    </v-col>

                    <!-- Min Samples -->
                    <v-col cols="12" md="4">
                      <v-slider
                        v-model="params.minSamples"
                        label="Mín. Muestras"
                        :min="1"
                        :max="20"
                        :step="1"
                        thumb-label
                        :disabled="
                          !['dbscan', 'hdbscan'].includes(params.algorithm)
                        "
                      >
                        <template #append>
                          <v-chip size="small" color="secondary">
                            {{ params.minSamples }}
                          </v-chip>
                        </template>
                      </v-slider>
                      <div class="text-caption text-grey">
                        Puntos mínimos para cluster (DBSCAN/HDBSCAN)
                      </div>
                    </v-col>

                    <!-- Min Cluster Size -->
                    <v-col cols="12" md="4">
                      <v-slider
                        v-model="params.minClusterSize"
                        label="Tamaño Mín. Cluster"
                        :min="1"
                        :max="15"
                        :step="1"
                        thumb-label
                      >
                        <template #append>
                          <v-chip size="small" color="success">
                            {{ params.minClusterSize }}
                          </v-chip>
                        </template>
                      </v-slider>
                      <div class="text-caption text-grey">
                        Filtrar clusters pequeños
                      </div>
                    </v-col>
                  </v-row>

                  <!-- UMAP Parameters Section -->
                  <v-divider class="my-4"></v-divider>
                  <div class="text-subtitle-1 mb-3 d-flex align-center">
                    <v-icon class="mr-2" color="purple">mdi-axis-arrow</v-icon>
                    <span class="font-weight-bold"
                      >UMAP - Reducción de Dimensionalidad</span
                    >
                    <v-chip size="small" color="purple" class="ml-2"
                      >Mejora Visual</v-chip
                    >
                  </div>
                  <v-row>
                    <!-- Enable UMAP -->
                    <v-col cols="12" md="4">
                      <v-switch
                        v-model="params.useUmap"
                        label="Activar UMAP"
                        color="purple"
                        hint="Mejora la separación visual de clusters"
                        persistent-hint
                        inset
                      >
                        <template #label>
                          <span class="font-weight-medium">Activar UMAP</span>
                        </template>
                      </v-switch>
                    </v-col>

                    <!-- UMAP N Neighbors -->
                    <v-col cols="12" md="4">
                      <v-slider
                        v-model="params.umapNNeighbors"
                        label="N Neighbors"
                        :min="5"
                        :max="50"
                        :step="1"
                        thumb-label
                        :disabled="!params.useUmap"
                        color="purple"
                      >
                        <template #append>
                          <v-chip size="small" color="purple">
                            {{ params.umapNNeighbors }}
                          </v-chip>
                        </template>
                      </v-slider>
                      <div class="text-caption text-grey">
                        Balance estructura local/global (↑ más global)
                      </div>
                    </v-col>

                    <!-- UMAP Min Dist -->
                    <v-col cols="12" md="4">
                      <v-slider
                        v-model="params.umapMinDist"
                        label="Min Dist"
                        :min="0.0"
                        :max="0.99"
                        :step="0.01"
                        thumb-label
                        :disabled="!params.useUmap"
                        color="purple"
                      >
                        <template #append>
                          <v-chip size="small" color="purple">
                            {{ params.umapMinDist.toFixed(2) }}
                          </v-chip>
                        </template>
                      </v-slider>
                      <div class="text-caption text-grey">
                        Distancia mínima entre puntos (↓ más compacto)
                      </div>
                    </v-col>
                  </v-row>

                  <v-alert
                    v-if="params.useUmap"
                    type="info"
                    variant="tonal"
                    density="compact"
                    class="mt-3"
                    icon="mdi-information"
                  >
                    <div class="text-caption">
                      <strong>UMAP activado:</strong> Los embeddings de 384
                      dimensiones se reducirán a 2D para mejor visualización.
                      Esto mejora la separación visual de clusters y facilita la
                      interpretación del grafo.
                    </div>
                  </v-alert>
                  <!-- Link pruning controls -->
                  <v-row class="mt-3">
                    <v-col cols="12" md="4">
                      <v-slider
                        v-model="params.topKLinks"
                        label="Top-K Enlaces"
                        :min="0"
                        :max="10"
                        :step="1"
                        thumb-label
                        :disabled="!params.useUmap"
                      >
                        <template #append>
                          <v-chip size="small" color="purple">
                            {{ params.topKLinks }}
                          </v-chip>
                        </template>
                      </v-slider>
                      <div class="text-caption text-grey">
                        Número máximo de enlaces por nodo (0 = ninguno)
                      </div>
                    </v-col>

                    <v-col cols="12" md="4">
                      <v-slider
                        v-model="params.linkThreshold"
                        label="Umbral Similitud"
                        :min="0.0"
                        :max="1.0"
                        :step="0.01"
                        thumb-label
                        :disabled="!params.useUmap"
                        color="purple"
                      >
                        <template #append>
                          <v-chip size="small" color="purple">
                            {{ (params.linkThreshold * 100).toFixed(0) }}%
                          </v-chip>
                        </template>
                      </v-slider>
                      <div class="text-caption text-grey">
                        Filtra enlaces por similitud mínima
                      </div>
                    </v-col>
                  </v-row>
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>

            <!-- Apply Button -->
            <v-row class="mt-4">
              <v-col cols="12">
                <v-btn
                  color="primary"
                  variant="flat"
                  @click="loadClusters"
                  :loading="loading"
                  block
                  size="large"
                >
                  <v-icon start>mdi-play</v-icon>
                  Aplicar Clustering
                </v-btn>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Statistics Cards -->
    <v-row class="mt-4">
      <v-col cols="6" md="3">
        <v-card color="primary" dark elevation="2">
          <v-card-text>
            <div class="d-flex align-center justify-space-between">
              <div>
                <div class="text-h4 font-weight-bold">
                  {{ clusterData.total_documents || 0 }}
                </div>
                <div class="text-caption">Total Documentos</div>
              </div>
              <v-icon size="48" opacity="0.3"
                >mdi-file-document-multiple</v-icon
              >
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="6" md="3">
        <v-card color="success" dark elevation="2">
          <v-card-text>
            <div class="d-flex align-center justify-space-between">
              <div>
                <div class="text-h4 font-weight-bold">
                  {{ clusterData.cluster_count || 0 }}
                </div>
                <div class="text-caption">Clusters Formados</div>
              </div>
              <v-icon size="48" opacity="0.3">mdi-chart-bubble</v-icon>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="6" md="3">
        <v-card color="warning" dark elevation="2">
          <v-card-text>
            <div class="d-flex align-center justify-space-between">
              <div>
                <div class="text-h4 font-weight-bold">
                  {{ clusterData.noise_count || 0 }}
                </div>
                <div class="text-caption">Sin Cluster (Ruido)</div>
              </div>
              <v-icon size="48" opacity="0.3">mdi-dots-hexagon</v-icon>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="6" md="3">
        <v-card color="info" dark elevation="2">
          <v-card-text>
            <div class="d-flex align-center justify-space-between">
              <div>
                <div class="text-h4 font-weight-bold">
                  {{ visibleNodesCount }}
                </div>
                <div class="text-caption">Nodos Visibles</div>
              </div>
              <v-icon size="48" opacity="0.3">mdi-eye</v-icon>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Main Content: Graph + Clusters List + Document List -->
    <v-row class="mt-4">
      <!-- Clusters List (Left Sidebar) -->
      <v-col cols="12" md="3" lg="2">
        <v-card elevation="2" class="clusters-sidebar">
          <v-card-title class="bg-primary text-white">
            <v-icon class="mr-2" color="white">mdi-format-list-bulleted</v-icon>
            Clusters
          </v-card-title>
          <v-card-text class="pa-0" style="max-height: 600px; overflow-y: auto">
            <v-list
              v-if="
                clusterData.cluster_stats &&
                clusterData.cluster_stats.length > 0
              "
            >
              <v-list-item
                v-for="cluster in clusterData.cluster_stats"
                :key="cluster.cluster_id"
                :class="{
                  'bg-blue-lighten-4': selectedCluster === cluster.cluster_id,
                }"
                @click="selectCluster(cluster.cluster_id)"
                class="cluster-list-item"
              >
                <template #prepend>
                  <v-avatar
                    :color="getClusterColor(cluster.cluster_id)"
                    size="40"
                  >
                    <span class="text-white font-weight-bold text-caption">
                      {{ cluster.cluster_id === -1 ? "?" : cluster.cluster_id }}
                    </span>
                  </v-avatar>
                </template>

                <v-list-item-title class="font-weight-medium text-caption">
                  {{
                    cluster.cluster_id === -1
                      ? "Sin Cluster"
                      : `Cluster ${cluster.cluster_id}`
                  }}
                </v-list-item-title>

                <v-list-item-subtitle class="text-caption">
                  <div>
                    {{ cluster.size }} doc{{ cluster.size !== 1 ? "s" : "" }}
                  </div>
                  <div v-if="cluster.dominant_area">
                    <v-icon
                      size="x-small"
                      :color="getLegalAreaColor(cluster.dominant_area)"
                    >
                      {{ getLegalAreaIcon(cluster.dominant_area) }}
                    </v-icon>
                    {{ cluster.dominant_area }}
                  </div>
                </v-list-item-subtitle>

                <template #append>
                  <v-icon
                    size="small"
                    :color="
                      selectedCluster === cluster.cluster_id
                        ? 'primary'
                        : 'grey'
                    "
                  >
                    {{
                      selectedCluster === cluster.cluster_id
                        ? "mdi-eye"
                        : "mdi-eye-outline"
                    }}
                  </v-icon>
                </template>
              </v-list-item>
            </v-list>

            <v-alert
              v-else
              type="info"
              variant="tonal"
              class="ma-2 text-caption"
            >
              No hay clusters disponibles
            </v-alert>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- Graph Visualization (Center) -->
      <v-col
        cols="12"
        :md="selectedClusterDocuments.length > 0 ? 6 : 9"
        :lg="selectedClusterDocuments.length > 0 ? 7 : 10"
      >
        <v-card elevation="2">
          <v-card-title
            class="bg-primary text-white d-flex align-center justify-space-between"
          >
            <div>
              <v-icon class="mr-2" color="white">mdi-graph</v-icon>
              Grafo de Clusters
            </div>
            <div class="d-flex gap-2">
              <v-chip size="small" variant="text" color="white">
                {{ visibleNodesCount }} nodos
              </v-chip>
              <v-btn
                icon="mdi-download"
                size="small"
                variant="text"
                color="white"
                @click="downloadGraph"
              >
                <v-icon>mdi-download</v-icon>
                <v-tooltip activator="parent" location="bottom">
                  Descargar imagen
                </v-tooltip>
              </v-btn>
            </div>
          </v-card-title>

          <v-card-text class="pa-0">
            <!-- ECharts Graph -->
            <div
              class="graph-container"
              ref="graphContainer"
              style="height: 600px"
            >
              <v-chart
                v-if="chartOptions && !loading"
                :option="chartOptions"
                autoresize
                @click="handleNodeClick"
                ref="chartRef"
              />

              <!-- Loading State -->
              <div
                v-if="loading"
                class="d-flex flex-column align-center justify-center"
                style="height: 100%"
              >
                <v-progress-circular
                  indeterminate
                  color="primary"
                  size="64"
                ></v-progress-circular>
                <div class="text-h6 mt-4 text-grey">
                  Procesando clustering...
                </div>
              </div>

              <!-- Empty State -->
              <div
                v-if="!loading && !chartOptions"
                class="d-flex flex-column align-center justify-center"
                style="height: 100%"
              >
                <v-icon size="120" color="grey-lighten-2"
                  >mdi-chart-bubble</v-icon
                >
                <div class="text-h6 mt-4 text-grey">
                  Aplica los parámetros de clustering para visualizar
                </div>
              </div>
            </div>
          </v-card-text>
        </v-card>

        <!-- Legend -->
        <v-card elevation="2" class="mt-4">
          <v-card-title>
            <v-icon class="mr-2">mdi-information</v-icon>
            Leyenda
          </v-card-title>
          <v-card-text>
            <v-row>
              <!-- Legal Areas Legend -->
              <v-col cols="12" md="6">
                <div class="text-subtitle-2 mb-2 font-weight-bold">
                  Colores por Área Legal:
                </div>
                <div class="d-flex flex-wrap gap-2">
                  <v-chip
                    v-for="area in visibleLegalAreas"
                    :key="area.name"
                    size="small"
                    :color="area.color"
                  >
                    <v-icon start size="small">{{ area.icon }}</v-icon>
                    {{ area.name }}
                  </v-chip>
                </div>
              </v-col>

              <!-- Document Types Legend -->
              <v-col cols="12" md="6">
                <div class="text-subtitle-2 mb-2 font-weight-bold">
                  Iconos por Tipo de Documento:
                </div>
                <div class="d-flex flex-wrap gap-2">
                  <v-chip
                    v-for="docType in visibleDocTypes"
                    :key="docType.name"
                    size="small"
                    variant="tonal"
                  >
                    <v-icon start size="small">{{ docType.icon }}</v-icon>
                    {{ docType.name }}
                  </v-chip>
                </div>
              </v-col>
            </v-row>

            <v-divider class="my-3"></v-divider>

            <div class="text-caption text-grey">
              <strong>Interacción:</strong> Click en nodo para ver detalles •
              Scroll para zoom • Arrastra para mover
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- Document List (Right Panel) - Only when cluster selected -->
      <v-col v-if="selectedClusterDocuments.length > 0" cols="12" md="3">
        <ClusterDocumentsList
          :cluster-id="selectedCluster"
          :documents="selectedClusterDocuments"
          :cluster-color="getClusterColor(selectedCluster)"
          @close="selectedCluster = null"
          @view-document="openDocumentDetails"
        />
      </v-col>
    </v-row>

    <!-- Document Details Dialog -->
    <v-dialog
      v-model="showDocumentDialog"
      max-width="1200"
      scrollable
      @update:model-value="(val) => !val && closeDocumentDialog()"
    >
      <v-card v-if="selectedDocument">
        <v-card-title
          class="bg-primary text-white d-flex align-center justify-space-between"
        >
          <div>
            <v-icon class="mr-2" color="white">mdi-file-document</v-icon>
            Detalles del Documento
          </div>
          <v-btn
            icon="mdi-close"
            variant="text"
            color="white"
            size="small"
            @click="closeDocumentDialog"
          ></v-btn>
        </v-card-title>

        <v-card-text class="pa-0">
          <v-row no-gutters>
            <!-- Document Details (Left) -->
            <v-col cols="12" md="6" class="pa-4 border-e">
              <div class="mb-3">
                <div class="text-overline text-grey">
                  Información del Documento
                </div>
                <h2 class="text-h6 mb-2">
                  {{ selectedDocument.title || "Sin título" }}
                </h2>
              </div>

              <!-- Document Info -->
              <v-list density="compact">
                <v-list-item>
                  <template #prepend>
                    <v-icon color="primary">mdi-folder</v-icon>
                  </template>
                  <v-list-item-title>Expediente</v-list-item-title>
                  <v-list-item-subtitle>{{
                    selectedDocument.case_number || "N/A"
                  }}</v-list-item-subtitle>
                </v-list-item>

                <v-list-item>
                  <template #prepend>
                    <v-icon
                      :color="
                        getLegalAreaColor(
                          getLegalAreaValue(selectedDocument.legal_area)
                        )
                      "
                    >
                      {{
                        getLegalAreaIcon(
                          getLegalAreaValue(selectedDocument.legal_area)
                        )
                      }}
                    </v-icon>
                  </template>
                  <v-list-item-title>Área Legal</v-list-item-title>
                  <v-list-item-subtitle>{{
                    getLegalAreaValue(selectedDocument.legal_area)
                  }}</v-list-item-subtitle>
                </v-list-item>

                <v-list-item>
                  <template #prepend>
                    <v-icon>{{
                      getDocumentIcon(
                        getDocTypeValue(selectedDocument.doc_type)
                      )
                    }}</v-icon>
                  </template>
                  <v-list-item-title>Tipo de Documento</v-list-item-title>
                  <v-list-item-subtitle>{{
                    getDocTypeValue(selectedDocument.doc_type)
                  }}</v-list-item-subtitle>
                </v-list-item>

                <v-list-item v-if="selectedDocument.document_date">
                  <template #prepend>
                    <v-icon color="info">mdi-calendar</v-icon>
                  </template>
                  <v-list-item-title>Fecha</v-list-item-title>
                  <v-list-item-subtitle>{{
                    formatDate(selectedDocument.document_date)
                  }}</v-list-item-subtitle>
                </v-list-item>

                <v-list-item>
                  <template #prepend>
                    <v-icon :color="getClusterColor(selectedDocument.cluster)"
                      >mdi-chart-bubble</v-icon
                    >
                  </template>
                  <v-list-item-title>Cluster</v-list-item-title>
                  <v-list-item-subtitle>
                    {{
                      selectedDocument.cluster === -1
                        ? "Sin cluster"
                        : `Cluster ${selectedDocument.cluster}`
                    }}
                  </v-list-item-subtitle>
                </v-list-item>
              </v-list>

              <v-divider class="my-3"></v-divider>

              <!-- Summary -->
              <div class="mb-3">
                <div class="text-overline text-grey mb-2">Resumen</div>
                <div
                  class="text-body-2"
                  style="max-height: 200px; overflow-y: auto"
                >
                  {{ selectedDocument.summary || "Sin resumen disponible" }}
                </div>
              </div>

              <v-btn
                block
                color="primary"
                prepend-icon="mdi-eye"
                @click="viewFullDocument(selectedDocument.id)"
              >
                Ver Documento Completo
              </v-btn>
            </v-col>

            <!-- Similar Documents (Right) -->
            <v-col cols="12" md="6" class="pa-4">
              <div class="mb-3">
                <div
                  class="text-overline text-grey d-flex align-center justify-space-between"
                >
                  <span>Documentos Similares en este Cluster</span>
                  <v-chip
                    v-if="!loadingSimilarDocs && similarDocuments.length > 0"
                    size="x-small"
                    color="primary"
                  >
                    {{ similarDocuments.length }}
                  </v-chip>
                </div>
                <div
                  v-if="!loadingSimilarDocs && similarDocuments.length > 0"
                  class="text-caption text-grey-darken-1"
                >
                  Ordenados por similitud (mayor a menor)
                </div>
              </div>

              <div v-if="loadingSimilarDocs" class="text-center py-8">
                <v-progress-circular
                  indeterminate
                  color="primary"
                ></v-progress-circular>
                <div class="text-caption mt-2">
                  Cargando documentos similares...
                </div>
              </div>

              <v-list v-else-if="similarDocuments.length > 0" lines="two">
                <v-list-item
                  v-for="doc in similarDocuments"
                  :key="doc.document_id || doc.id"
                  @click="openDocumentDetails(doc.document_id || doc.id)"
                  class="similar-doc-item"
                >
                  <template #prepend>
                    <v-avatar
                      :color="
                        getLegalAreaColor(getLegalAreaValue(doc.legal_area))
                      "
                      size="40"
                    >
                      <v-icon color="white" size="20">
                        {{ getDocumentIcon(getDocTypeValue(doc.doc_type)) }}
                      </v-icon>
                    </v-avatar>
                  </template>

                  <v-list-item-title class="text-body-2">
                    {{ doc.title || "Sin título" }}
                  </v-list-item-title>

                  <v-list-item-subtitle class="text-caption">
                    {{ doc.case_number || "Sin expediente" }}
                  </v-list-item-subtitle>

                  <template #append>
                    <!-- Debug: Mostrar siempre para verificar -->
                    <div class="d-flex flex-column align-end">
                      <v-chip
                        v-if="
                          doc.similarity !== undefined &&
                          doc.similarity !== null
                        "
                        size="small"
                        :color="getSimilarityChipColor(doc.similarity)"
                        variant="flat"
                      >
                        {{ (doc.similarity * 100).toFixed(1) }}%
                      </v-chip>
                      <!-- Debug chip temporal -->
                      <span v-else class="text-caption text-grey">
                        {{
                          doc.similarity === undefined
                            ? "undefined"
                            : doc.similarity === null
                            ? "null"
                            : "sin valor"
                        }}
                      </span>
                    </div>
                  </template>
                </v-list-item>
              </v-list>

              <v-alert v-else type="info" variant="tonal" class="text-caption">
                No hay otros documentos en este cluster
              </v-alert>
            </v-col>
          </v-row>
        </v-card-text>

        <v-card-actions class="px-4 py-3">
          <v-spacer></v-spacer>
          <v-btn color="grey" variant="text" @click="closeDocumentDialog">
            Cerrar
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from "vue";
import { useRouter } from "vue-router";
import axios from "axios";
import VChart from "vue-echarts";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { GraphChart } from "echarts/charts";
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
} from "echarts/components";
import { useColors } from "@/composables/useColors";
import { useDocumentIcons } from "@/composables/useDocumentIcons";
import ClusterDocumentsList from "@/components/ClusterDocumentsList.vue";

// Register ECharts components
use([
  CanvasRenderer,
  GraphChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
]);

const router = useRouter();

// Composables
const { getClusterColor, getLegalAreaColor } = useColors();
const {
  getDocumentIcon,
  getLegalAreaIcon,
  getDocumentShape,
  getAllLegalAreas,
  getAllDocumentTypes,
} = useDocumentIcons();

// Algorithm Options
const algorithmOptions = ref([
  {
    label: "DBSCAN",
    value: "dbscan",
    description:
      "Density-based clustering - Detecta clusters de forma arbitraria",
  },
  {
    label: "HDBSCAN",
    value: "hdbscan",
    description: "Hierarchical DBSCAN - Más robusto y adaptativo",
  },
  {
    label: "K-Means",
    value: "kmeans",
    description: "Clustering por centroides - Requiere número de clusters",
  },
  {
    label: "Agglomerative",
    value: "agglomerative",
    description: "Clustering jerárquico - Agrupa progresivamente",
  },
]);

const metricOptions = ref([
  { label: "Coseno (recomendado)", value: "cosine" },
  { label: "Euclidiana", value: "euclidean" },
  { label: "Manhattan", value: "manhattan" },
]);

const embeddingOptions = ref([
  { label: "Simple (Rápido)", value: false },
  { label: "Mejorado (Más preciso)", value: true },
]);

// State
const loading = ref(false);
const clusterData = ref({
  nodes: [],
  links: [],
  clusters: {},
  cluster_stats: [],
  total_documents: 0,
  cluster_count: 0,
  noise_count: 0,
});

const params = ref({
  algorithm: "dbscan",
  metric: "cosine",
  nClusters: 5,
  eps: 0.05,
  minSamples: 2,
  minClusterSize: 2,
  maxDocuments: 200,
  useEnhancedEmbedding: false,
  // UMAP parameters
  useUmap: true,
  umapNNeighbors: 15,
  umapMinDist: 0.1,
  // Link pruning
  topKLinks: 3,
  linkThreshold: 0.3,
});

const selectedCluster = ref(null);
const chartRef = ref(null);
const graphContainer = ref(null);

// Dialog state
const showDocumentDialog = ref(false);
const selectedDocument = ref(null);
const similarDocuments = ref([]);
const loadingSimilarDocs = ref(false);

// Computed
const visibleNodesCount = computed(() => {
  if (selectedCluster.value !== null) {
    return clusterData.value.nodes.filter(
      (node) => node.cluster === selectedCluster.value
    ).length;
  }
  return clusterData.value.nodes.length;
});

const selectedClusterDocuments = computed(() => {
  if (selectedCluster.value === null) return [];

  return clusterData.value.nodes
    .filter((node) => node.cluster === selectedCluster.value)
    .map((node) => ({
      id: node.id,
      title: node.title,
      case_number: node.case_number,
      legal_area: node.legal_area,
      doc_type: node.doc_type,
      summary: node.summary,
      document_date: node.document_date,
      resolution_number: node.resolution_number,
    }));
});

const visibleLegalAreas = computed(() => {
  const areasInData = new Set(
    clusterData.value.nodes.map((node) => node.legal_area).filter(Boolean)
  );

  return getAllLegalAreas().filter((area) => areasInData.has(area.name));
});

const visibleDocTypes = computed(() => {
  const typesInData = new Set(
    clusterData.value.nodes.map((node) => node.doc_type).filter(Boolean)
  );

  const allTypes = getAllDocumentTypes();
  return allTypes.filter((type) =>
    Array.from(typesInData).some((t) =>
      t.toLowerCase().includes(type.name.toLowerCase())
    )
  );
});

// ECharts Options
const chartOptions = computed(() => {
  if (!clusterData.value.nodes || clusterData.value.nodes.length === 0) {
    return null;
  }

  // Filter nodes and links based on selected cluster
  let nodes = clusterData.value.nodes;
  let links = clusterData.value.links;

  if (selectedCluster.value !== null) {
    nodes = nodes.filter((node) => node.cluster === selectedCluster.value);
    const nodeIds = new Set(nodes.map((n) => n.id));
    links = links.filter(
      (link) => nodeIds.has(link.source) && nodeIds.has(link.target)
    );
  }

  // Check if UMAP coordinates are available
  const hasUmapCoords =
    nodes.length > 0 && nodes[0].x !== undefined && nodes[0].y !== undefined;

  // Transform nodes for ECharts
  const graphNodes = nodes.map((node) => {
    const baseNode = {
      id: node.id,
      name: node.label || node.title?.substring(0, 30) + "...",
      value: node.val || 10,
      symbolSize: (node.val || 10) * 3,
      symbol: getEChartsSymbol(node.doc_type),
      itemStyle: {
        color: getLegalAreaColor(node.legal_area),
        borderColor: node.is_central ? "#FF9800" : "#fff",
        borderWidth: node.is_central ? 3 : 1,
      },
      label: {
        show: true,
        fontSize: 10,
        color: "#333",
      },
      // Store full data for tooltip
      ...node,
    };

    // If UMAP coordinates are available, use them for fixed positioning
    if (hasUmapCoords) {
      baseNode.x = node.x * 1000; // Scale up for better visualization
      baseNode.y = node.y * 1000;
      baseNode.fixed = true; // Fix nodes at UMAP coordinates
    }

    return baseNode;
  });

  // Transform links for ECharts
  const graphLinks = links.map((link) => ({
    source: link.source,
    target: link.target,
    value: link.value,
    lineStyle: {
      width: Math.max(1, (link.value || 0.5) * 3),
      color: getEdgeColor(link.value || 0.5),
      opacity: Math.max(0.25, Math.min(0.9, link.value || 0.5)),
      curveness: 0, // Líneas rectas
    },
  }));

  return {
    tooltip: {
      trigger: "item",
      formatter: (params) => {
        if (params.dataType === "node") {
          const node = params.data;
          return `
            <div style="max-width: 300px;">
              <div style="font-weight: bold; margin-bottom: 8px;">${
                node.title || "Sin título"
              }</div>
              <div><strong>Expediente:</strong> ${
                node.case_number || "N/A"
              }</div>
              <div><strong>Área Legal:</strong> ${
                node.legal_area || "N/A"
              }</div>
              <div><strong>Tipo:</strong> ${node.doc_type || "N/A"}</div>
              <div><strong>Cluster:</strong> ${
                node.cluster === -1 ? "Sin cluster" : node.cluster
              }</div>
              ${
                hasUmapCoords
                  ? '<div style="margin-top: 4px;"><em>Posición UMAP</em></div>'
                  : ""
              }
            </div>
          `;
        } else if (params.dataType === "edge") {
          const similarity = (params.value * 100).toFixed(1);
          return `Similitud: ${similarity}%`;
        }
        return "";
      },
    },
    series: [
      {
        type: "graph",
        layout: hasUmapCoords ? "none" : "force", // Use 'none' layout if UMAP coords available
        data: graphNodes,
        links: graphLinks,
        roam: true,
        label: {
          show: true,
          position: "right",
          formatter: "{b}",
        },
        labelLayout: {
          hideOverlap: true,
        },
        force: hasUmapCoords
          ? undefined
          : {
              repulsion: 1000,
              gravity: 0.1,
              edgeLength: [100, 200],
              layoutAnimation: true,
            },
        emphasis: {
          focus: "adjacency",
          lineStyle: {
            width: 5,
          },
        },
      },
    ],
  };
});

// Methods
const getEChartsSymbol = (docType) => {
  const shape = getDocumentShape(docType);
  const mapping = {
    circle: "circle",
    rect: "rect",
    triangle: "triangle",
    diamond: "diamond",
  };
  return mapping[shape] || "circle";
};

const getEdgeColor = (similarity) => {
  if (similarity >= 0.8) {
    const intensity = Math.floor(((similarity - 0.8) / 0.2) * 50);
    return `rgb(${50 - intensity}, ${50 - intensity}, ${50 - intensity})`;
  } else if (similarity >= 0.6) {
    const intensity = Math.floor(((similarity - 0.6) / 0.2) * 70);
    return `rgb(${120 - intensity}, ${120 - intensity}, ${120 - intensity})`;
  } else if (similarity >= 0.4) {
    const intensity = Math.floor(((similarity - 0.4) / 0.2) * 70);
    return `rgb(${190 - intensity}, ${190 - intensity}, ${190 - intensity})`;
  } else {
    const intensity = Math.floor((similarity / 0.4) * 55);
    return `rgb(${245 - intensity}, ${245 - intensity}, ${245 - intensity})`;
  }
};

const loadClusters = async () => {
  loading.value = true;

  try {
    const response = await axios.get(
      "http://localhost:8000/api/documents/all_clusters/",
      {
        params: {
          algorithm: params.value.algorithm,
          metric: params.value.metric,
          n_clusters: params.value.nClusters,
          eps: params.value.eps,
          min_samples: params.value.minSamples,
          min_cluster_size: params.value.minClusterSize,
          max_documents: params.value.maxDocuments,
          use_enhanced_embedding: params.value.useEnhancedEmbedding,
          // UMAP parameters
          use_umap: params.value.useUmap,
          umap_n_neighbors: params.value.umapNNeighbors,
          umap_min_dist: params.value.umapMinDist,
          // Link pruning parameters
          top_k_links: params.value.topKLinks,
          link_threshold: params.value.linkThreshold,
        },
      }
    );

    clusterData.value = response.data;
    selectedCluster.value = null;
  } catch (error) {
    console.error("Error loading clusters:", error);
  } finally {
    loading.value = false;
  }
};

const selectCluster = (clusterId) => {
  selectedCluster.value =
    selectedCluster.value === clusterId ? null : clusterId;
};

const handleNodeClick = (params) => {
  if (params.dataType === "node") {
    openDocumentDetails(params.data.id);
  }
};

const openDocumentDetails = async (docId) => {
  try {
    // Find the document in the cluster data
    const doc = clusterData.value.nodes.find((node) => node.id === docId);
    if (!doc) {
      console.error("Document not found:", docId);
      return;
    }

    selectedDocument.value = doc;
    showDocumentDialog.value = true;

    // Load similar documents from the same cluster
    await loadSimilarDocuments(doc.cluster, docId);
  } catch (error) {
    console.error("Error opening document details:", error);
  }
};

const closeDocumentDialog = () => {
  showDocumentDialog.value = false;
  selectedDocument.value = null;
  similarDocuments.value = [];
};

const loadSimilarDocuments = async (clusterId, excludeDocId) => {
  console.log(
    "Loading similar documents for cluster:",
    clusterId,
    "excluding doc:",
    excludeDocId
  );

  if (clusterId === -1) {
    // No cluster (noise)
    console.log("Document is noise (cluster -1), no similar documents");
    similarDocuments.value = [];
    return;
  }

  loadingSimilarDocs.value = true;
  try {
    const requestParams = {
      cluster_id: clusterId,
      reference_doc_id: excludeDocId, // ✅ Agregar documento de referencia para calcular similitud
      algorithm: params.value.algorithm,
      metric: params.value.metric,
      n_clusters: params.value.nClusters,
      eps: params.value.eps,
      min_samples: params.value.minSamples,
      min_cluster_size: params.value.minClusterSize,
      max_documents: params.value.maxDocuments,
      use_enhanced_embedding: params.value.useEnhancedEmbedding,
    };

    console.log("Request params:", requestParams);

    const response = await axios.get("/api/documents/cluster_documents/", {
      params: requestParams,
    });

    console.log("Response data:", response.data);

    // The response has a 'documents' field
    const docs = response.data.documents || [];

    console.log("Total documents in cluster:", docs.length);
    console.log("Has similarity calculated:", response.data.has_similarity);
    console.log("Excluding document ID:", excludeDocId);

    // Log first document to see structure
    if (docs.length > 0) {
      console.log("Sample document structure:", {
        id: docs[0].id,
        document_id: docs[0].document_id,
        title: docs[0].title?.substring(0, 30),
        similarity: docs[0].similarity,
        has_similarity_field: "similarity" in docs[0],
      });
    }

    // Filter out the current document (use document_id from serializer)
    const filtered = docs.filter((doc) => {
      const docId = doc.document_id || doc.id;
      return docId !== excludeDocId;
    });

    console.log("Filtered documents (excluding current):", filtered.length);

    // Sort by similarity (descending) if similarity is available
    const sorted = filtered.sort((a, b) => {
      const simA = a.similarity || 0;
      const simB = b.similarity || 0;
      return simB - simA;
    });

    // Limit to top 10 most similar documents
    similarDocuments.value = sorted.slice(0, 10);

    console.log("Similar documents set:", similarDocuments.value.length);
    console.log(
      "Documents with similarity:",
      similarDocuments.value.map((d) => ({
        id: d.id,
        document_id: d.document_id,
        title: d.title?.substring(0, 30),
        similarity: d.similarity,
      }))
    );
  } catch (error) {
    console.error("Error loading similar documents:", error);
    similarDocuments.value = [];
  } finally {
    loadingSimilarDocs.value = false;
  }
};

const getSimilarityChipColor = (similarity) => {
  if (!similarity && similarity !== 0) return "grey";
  if (similarity >= 0.9) return "success";
  if (similarity >= 0.7) return "info";
  if (similarity >= 0.5) return "warning";
  if (similarity >= 0.3) return "orange";
  return "error";
};

const formatDate = (dateString) => {
  if (!dateString) return "N/A";
  const date = new Date(dateString);
  return date.toLocaleDateString("es-ES", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
};

// Helper functions to handle fields that might be objects or strings
const getLegalAreaValue = (legalArea) => {
  if (!legalArea) return "N/A";
  if (typeof legalArea === "string") return legalArea;
  if (typeof legalArea === "object" && legalArea.name) return legalArea.name;
  return "N/A";
};

const getDocTypeValue = (docType) => {
  if (!docType) return "N/A";
  if (typeof docType === "string") return docType;
  if (typeof docType === "object" && docType.name) return docType.name;
  return "N/A";
};

const centerGraph = () => {
  if (chartRef.value) {
    const chart = chartRef.value;
    // Reset graph view to default state
    chart.dispatchAction({
      type: "restore",
    });
  }
};

const viewFullDocument = (docId) => {
  router.push({ name: "Home", query: { doc: docId } });
};

const downloadGraph = () => {
  if (chartRef.value) {
    const chart = chartRef.value;
    const url = chart.getDataURL({
      type: "png",
      pixelRatio: 2,
      backgroundColor: "#fff",
    });

    const link = document.createElement("a");
    link.href = url;
    link.download = `cluster-graph-${new Date().toISOString()}.png`;
    link.click();
  }
};

// Lifecycle
onMounted(() => {
  loadClusters();
});
</script>

<style scoped>
.clusters-view {
  max-width: 1920px;
  margin: 0 auto;
}

.clusters-sidebar {
  position: sticky;
  top: 80px;
}

.cluster-list-item {
  cursor: pointer;
  transition: background-color 0.2s;
}

.cluster-list-item:hover {
  background-color: rgba(0, 0, 0, 0.04);
}

.graph-container {
  position: relative;
}

.gap-2 {
  gap: 8px;
}

.similar-doc-item {
  cursor: pointer;
  transition: background-color 0.2s;
}

.similar-doc-item:hover {
  background-color: rgba(0, 0, 0, 0.04);
}
</style>
