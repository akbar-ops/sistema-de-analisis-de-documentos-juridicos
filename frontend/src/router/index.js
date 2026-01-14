import { createRouter, createWebHistory } from "vue-router";
import Home from "../views/Home.vue";
import QueueView from "../views/QueueView.vue";
import StatsView from "../views/StatsView.vue";
import ClustersView from "../views/ClustersView.vue";
import ClustersViewNew from "../views/ClustersViewNew.vue";
import ClustersViewD3 from "../views/ClustersViewD3.vue";
import ClustersViewECharts from "../views/ClustersViewECharts.vue";
import TopicsViewECharts from "../views/TopicsViewECharts.vue";
import SimpleUploadView from "../views/SimpleUploadView.vue";
import BERTopicView from "../views/BERTopicView.vue";

const routes = [
  {
    path: "/",
    name: "Home",
    component: Home,
    meta: {
      title: "Inicio - Docana",
    },
  },
  {
    path: "/simple",
    name: "SimpleUpload",
    component: SimpleUploadView,
    meta: {
      title: "Análisis de Documentos - Docana",
    },
  },
  {
    path: "/document/:id",
    name: "DocumentView",
    component: SimpleUploadView,
    meta: {
      title: "Vista de Documento - Docana",
    },
    props: true,
  },
  {
    path: "/queue",
    name: "Queue",
    component: QueueView,
    meta: {
      title: "Cola de Procesamiento - Docana",
    },
  },
  {
    path: "/stats",
    name: "Stats",
    component: StatsView,
    meta: {
      title: "Estadísticas - Docana",
    },
  },
  {
    path: "/clusters",
    redirect: "/clusters-echarts", // Redirect to new D3 version
  },
  {
    path: "/clusters-d3",
    name: "ClustersD3",
    component: ClustersViewD3,
    meta: {
      title: "Explorador de Clusters - Docana",
    },
  },
  {
    path: "/clusters-echarts",
    name: "ClustersECharts",
    component: ClustersViewECharts,
    meta: {
      title: "Explorador de Clusters (ECharts) - Docana",
    },
  },
  {
    path: "/clusters-vng",
    name: "ClustersVNG",
    component: ClustersViewNew,
    meta: {
      title: "Explorador de Clusters (v-network-graph) - Docana",
    },
  },
  {
    path: "/clusters-old",
    name: "ClustersOld",
    component: ClustersView,
    meta: {
      title: "Explorador de Clusters (OLD) - Docana",
    },
  },
  {
    path: "/bertopic",
    name: "BERTopic",
    component: BERTopicView,
    meta: {
      title: "Topic Modeling (BERTopic) - Docana",
    },
  },
  {
    path: "/topics",
    name: "TopicsECharts",
    component: TopicsViewECharts,
    meta: {
      title: "Explorador de Tópicos - Docana",
    },
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
  // Scroll to top on route change
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition;
    }
    return { top: 0 };
  },
});

// Update document title on route change
router.beforeEach((to, from, next) => {
  document.title = to.meta.title || "Docana";
  next();
});

// Force layout recalculation after navigation
router.afterEach((to, from) => {
  // Trigger a reflow to ensure the view renders properly
  setTimeout(() => {
    window.dispatchEvent(new Event("resize"));
  }, 100);
});

export default router;
