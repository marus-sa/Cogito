<script setup>
import { onMounted, ref } from 'vue'
import { Check, UsersRound, X } from 'lucide-vue-next'
import { useMessagesStore } from '../stores/messages'
import { api } from '../api'
import BaseButton from '../components/BaseButton.vue'
const messages = useMessagesStore()
const pendingTutors = ref([])
async function loadApplications() {
  try {
    const data = await api('/admin/users?status=pending')
    pendingTutors.value = data.items.filter((user) => user.role === 'tutor')
  } catch (error) {
    messages.showToast(error.message, 'error')
  }
}
async function approve(user) {
  try {
    await api(`/admin/users/${user.id}`, { method: 'PATCH', body: JSON.stringify({ accountStatus: 'active' }) })
    pendingTutors.value = pendingTutors.value.filter((item) => item.id !== user.id)
    messages.showToast(`Заявка ${user.name} подтверждена`)
  } catch (error) {
    messages.showToast(error.message, 'error')
  }
}
async function reject(user) {
  try {
    await api(`/admin/users/${user.id}`, { method: 'PATCH', body: JSON.stringify({ accountStatus: 'blocked' }) })
    pendingTutors.value = pendingTutors.value.filter((item) => item.id !== user.id)
    messages.showToast(`Заявка ${user.name} отклонена`)
  } catch (error) {
    messages.showToast(error.message, 'error')
  }
}
onMounted(loadApplications)
</script>
<template>
  <div class="page"><div class="page-heading"><div><h1>Заявки</h1><p>Здесь появляются реальные заявки репетиторов после регистрации.</p></div></div>
    <section class="card panel below"><div class="section-title"><h2>Заявки репетиторов</h2><span class="tag warning">{{ pendingTutors.length }} ожидают</span></div><div v-if="pendingTutors.length" class="applications"><article v-for="user in pendingTutors" :key="user.id"><span><UsersRound :size="17" /></span><div><b>{{ user.name }}</b><small>{{ user.email }} · {{ user.subjects || 'Предмет не указан' }}</small></div><div class="application-actions"><BaseButton size="sm" @click="approve(user)"><Check :size="15" /> Подтвердить</BaseButton><BaseButton size="sm" variant="outline" @click="reject(user)"><X :size="15" /> Отклонить</BaseButton></div></article></div><p v-else class="muted tiny">Новых заявок на проверку нет.</p></section>
    <section class="card panel below"><div class="section-title"><h2>Как обработать заявку</h2></div><ol class="steps"><li>Человек выбирает роль «Репетитор» и завершает регистрацию.</li><li>У вас появляется уведомление «Новая заявка репетитора».</li><li>Откройте этот раздел, проверьте имя, почту и предмет, затем подтвердите или отклоните заявку.</li><li>После подтверждения человек сможет войти в свой кабинет.</li></ol><p class="muted tiny">Ученики и родители получают доступ сразу. Если их тоже нужно подтверждать вручную, это можно включить отдельным правилом.</p></section>
  </div>
</template>
<style scoped>
.below{margin-top:19px}.applications{display:grid}.applications article{display:flex;align-items:center;gap:9px;padding:12px 0;border-top:1px solid var(--border)}.applications article>span{display:grid;place-items:center;width:34px;height:34px;color:var(--primary-dark);background:var(--primary-extra-light);border-radius:10px}.applications article>div{min-width:0;flex:1}.applications b,.applications small{display:block}.applications b{font-size:11px}.applications small{margin-top:3px;overflow:hidden;color:var(--text-secondary);font-size:10px;text-overflow:ellipsis;white-space:nowrap}.application-actions{display:flex;gap:6px}.steps{display:grid;gap:10px;margin:14px 0 12px;padding-left:20px;color:var(--text-secondary);font-size:11px;line-height:1.5}.steps li::marker{color:var(--primary-dark);font-weight:800}@media(max-width:620px){.applications article{align-items:flex-start;flex-wrap:wrap}.application-actions{width:100%;margin-left:43px}}
</style>
