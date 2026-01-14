<template>
  <div class="empty-state">
    <v-icon :size="iconSize" :color="iconColor">
      {{ icon }}
    </v-icon>
    <h3 v-if="title" class="empty-state__title mt-4">
      {{ title }}
    </h3>
    <p v-if="message" class="empty-state__message mt-2">
      {{ message }}
    </p>
    <slot name="actions" />
  </div>
</template>

<script setup>
const props = defineProps({
  icon: {
    type: String,
    default: "mdi-file-document-outline",
  },
  iconSize: {
    type: [String, Number],
    default: 64,
  },
  iconColor: {
    type: String,
    default: "grey-lighten-1",
  },
  title: {
    type: String,
    default: "",
  },
  message: {
    type: String,
    default: "",
  },
});
</script>

<style scoped lang="scss">
@import "@/styles/variables.scss";

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: $spacing-3xl $spacing-xl;
  text-align: center;

  &__title {
    color: rgba(0, 0, 0, 0.87);
    font-size: $font-size-lg;
    font-weight: $font-weight-medium;
  }

  &__message {
    color: rgba(0, 0, 0, 0.6);
    font-size: $font-size-sm;
    max-width: 400px;
  }
}
</style>
