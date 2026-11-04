<script setup>
defineProps({
  files: { type: Array, default: () => [] },
  removable: Boolean,
  busy: Boolean,
})
defineEmits(['remove'])
</script>

<template>
  <ul v-if="files.length" class="work-files">
    <li v-for="file in files" :key="file.id">
      <a :href="file.url" :download="file.name">{{ file.name }}</a>
      <small>{{ Math.max(1, Math.ceil(file.size / 1024)) }} КБ</small>
      <button v-if="removable" :disabled="busy" @click="$emit('remove', file)">
        Убрать файл
      </button>
    </li>
  </ul>
</template>

<style scoped>
.work-files {
  display: grid;
  gap: 10px;
  padding: 0;
  margin: 16px 0;
  list-style: none;
}
li { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
a { color: var(--primary-dark); overflow-wrap: anywhere; }
small { color: var(--text-secondary); }
button {
  border: 0;
  padding: 5px 8px;
  border-radius: 6px;
  background: var(--bg-main);
  color: var(--danger);
  cursor: pointer;
}
</style>
