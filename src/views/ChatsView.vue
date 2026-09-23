<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { Plus, Search, Send, Smile } from 'lucide-vue-next'
import { useMessagesStore } from '../stores/messages'
import UserAvatar from '../components/UserAvatar.vue'
import EmptyState from '../components/EmptyState.vue'
import BaseModal from '../components/BaseModal.vue'

const messagesStore = useMessagesStore()
const activeId = ref(null)
const draft = ref('')
const search = ref('')
const contactSearch = ref('')
const newDialogOpen = ref(false)
let refreshTimer

const dialogs = computed(() => messagesStore.dialogs)
const contacts = computed(() => messagesStore.contacts.filter((person) => person.name.toLowerCase().includes(contactSearch.value.toLowerCase())))
const active = computed(() => dialogs.value.find((item) => item.id === activeId.value) || null)
const messages = computed(() => messagesStore.messages)
const filteredDialogs = computed(() => dialogs.value.filter((item) => item.name.toLowerCase().includes(search.value.toLowerCase())))

async function selectDialog(id) {
  activeId.value = id
  try {
    await messagesStore.loadMessages(id)
  } catch (error) {
    messagesStore.showToast(error.message, 'error')
  }
}

async function loadChats() {
  try {
    await Promise.all([messagesStore.loadDialogs(), messagesStore.loadContacts()])
    if (!activeId.value && dialogs.value[0]) await selectDialog(dialogs.value[0].id)
  } catch (error) {
    messagesStore.showToast(error.message, 'error')
  }
}

async function startDialog(person) {
  try {
    const dialog = await messagesStore.startConversation(person.id)
    newDialogOpen.value = false
    await selectDialog(dialog.id)
  } catch (error) {
    messagesStore.showToast(error.message, 'error')
  }
}

async function send() {
  const text = draft.value.trim()
  if (!text || !activeId.value) return
  try {
    await messagesStore.send(activeId.value, text)
    draft.value = ''
  } catch (error) {
    messagesStore.showToast(error.message, 'error')
  }
}

onMounted(async () => {
  await loadChats()
  refreshTimer = window.setInterval(async () => {
    try {
      await messagesStore.loadDialogs()
      if (activeId.value) await messagesStore.loadMessages(activeId.value)
    } catch { /* Повторим обновление при следующем опросе. */ }
  }, 8000)
})

onBeforeUnmount(() => window.clearInterval(refreshTimer))
</script>
<template>
  <div class="page chat-page">
    <div class="page-heading"><div><h1>Чаты</h1><p>Переписывайтесь с координатором и участниками, связанными с вашим обучением.</p></div></div>
    <section class="chat-shell card">
      <aside class="dialogs">
        <div class="dialogs-head"><h2>Сообщения</h2><button aria-label="Новый диалог" @click="newDialogOpen = true"><Plus :size="17" /></button></div>
        <label class="dialog-search"><Search :size="15" /><input v-model="search" placeholder="Поиск диалогов" /></label>
        <div class="dialog-list">
          <button v-for="dialog in filteredDialogs" :key="dialog.id" class="dialog" :class="{ active: activeId === dialog.id }" @click="selectDialog(dialog.id)">
            <UserAvatar :initials="dialog.initials" :color="dialog.color" :size="38" />
            <span class="dialog-text"><span><b>{{ dialog.name }}</b><em>{{ dialog.time }}</em></span><small>{{ dialog.role }} · {{ dialog.last }}</small></span><i v-if="dialog.unread">{{ dialog.unread }}</i>
          </button>
          <EmptyState v-if="!filteredDialogs.length" title="Диалогов пока нет" text="Нажмите «+», чтобы написать человеку." />
        </div>
      </aside>
      <main v-if="active" class="conversation">
        <header><div class="person"><UserAvatar :initials="active.initials" :color="active.color" :size="39" /><span><b>{{ active.name }}</b><small>{{ active.role }}<template v-if="active.accountStatus === 'pending'"> · заявка ожидает решения</template></small></span></div></header>
        <div v-if="messages.length" class="message-area"><div class="date-separator">Переписка</div><div v-for="message in messages" :key="message.id" class="message" :class="message.sender"><p>{{ message.text }}</p><span>{{ message.time }} <i v-if="message.sender === 'me'">✓✓</i></span></div></div>
        <EmptyState v-else title="Сообщений пока нет" text="Напишите первое сообщение этому участнику." />
        <footer><input v-model="draft" placeholder="Напишите сообщение…" @keydown.enter.prevent="send" /><button aria-label="Добавить эмодзи" @click="draft += ' 🙂'"><Smile :size="19" /></button><button class="send" aria-label="Отправить" @click="send"><Send :size="18" /></button></footer>
      </main>
      <main v-else class="conversation chat-empty"><EmptyState title="Выберите диалог" text="Или нажмите «+», чтобы начать новый." /></main>
    </section>
    <BaseModal v-model="newDialogOpen" title="Новый диалог">
      <p class="modal-copy">Показываем только тех участников, с которыми вам разрешено переписываться.</p>
      <label class="dialog-search contact-search"><Search :size="15" /><input v-model="contactSearch" placeholder="Найти человека" /></label>
      <div class="contact-list"><button v-for="person in contacts" :key="person.id" class="contact-row" @click="startDialog(person)"><UserAvatar :initials="person.initials" :color="person.color" :size="38" /><span><b>{{ person.name }}</b><small>{{ person.role }}<template v-if="person.accountStatus === 'pending'"> · новая заявка</template></small></span></button><EmptyState v-if="!contacts.length" title="Контактов пока нет" text="После назначения связи здесь появятся нужные люди." /></div>
    </BaseModal>
  </div>
</template>
<style scoped>
.chat-shell{display:grid;grid-template-columns:270px minmax(340px,1fr);min-height:590px;overflow:hidden}.dialogs{background:#fcfbfe;border-right:1px solid var(--border)}.dialogs-head{display:flex;align-items:center;justify-content:space-between;padding:18px 16px 12px}.dialogs-head h2{margin:0;font-size:15px}.dialogs-head button{display:grid;place-items:center;width:28px;height:28px;border:0;border-radius:8px;color:#fff;background:var(--primary)}.dialog-search{position:relative;display:flex;align-items:center;margin:0 13px 10px;color:var(--text-secondary)}.dialog-search svg{position:absolute;left:9px}.dialog-search input{width:100%;min-height:33px;padding:0 9px 0 31px;border:1px solid var(--border);border-radius:9px;outline:0;background:#fff;font-size:10px}.dialog-list{display:grid}.dialog{position:relative;display:flex;align-items:center;gap:9px;width:100%;padding:11px 13px;border:0;color:var(--text-main);background:transparent;text-align:left}.dialog:hover,.dialog.active{background:var(--primary-extra-light)}.dialog.active::before{position:absolute;left:0;width:3px;height:34px;content:'';background:var(--primary);border-radius:0 3px 3px 0}.dialog-text{min-width:0;flex:1}.dialog-text>span{display:flex;justify-content:space-between;gap:4px}.dialog b{display:block;overflow:hidden;font-size:11px;text-overflow:ellipsis;white-space:nowrap}.dialog em{color:var(--text-secondary);font-size:9px;font-style:normal}.dialog small{display:block;margin-top:3px;overflow:hidden;color:var(--text-secondary);font-size:9px;text-overflow:ellipsis;white-space:nowrap}.dialog>i{display:grid;place-items:center;min-width:16px;height:16px;padding:0 3px;color:#fff;background:var(--primary);border-radius:50%;font-size:8px;font-style:normal;font-weight:800}.conversation{display:flex;flex-direction:column;min-width:0;background:#fff}.conversation>header{display:flex;align-items:center;min-height:65px;padding:0 18px;border-bottom:1px solid var(--border)}.person{display:flex;align-items:center;gap:9px}.person b,.person small{display:block}.person b{font-size:12px}.person small{margin-top:2px;color:var(--text-secondary);font-size:9px}.message-area{display:flex;flex:1;flex-direction:column;gap:9px;padding:18px;overflow-y:auto;background:linear-gradient(145deg,#fff,#fdfbff)}.date-separator{align-self:center;padding:4px 8px;color:#948a9e;background:#f2eff5;border-radius:100px;font-size:9px}.message{max-width:73%;padding:9px 10px;border-radius:13px 13px 13px 3px;background:#f1edf7}.message.me{align-self:flex-end;border-radius:13px 13px 3px 13px;color:#fff;background:var(--primary)}.message p{margin:0;font-size:11px;line-height:1.55}.message>span{display:block;margin-top:4px;color:#93899e;font-size:8px;text-align:right}.message.me>span{color:#e9defa}.message.me i{margin-left:3px;color:#d6f3e1;font-style:normal}footer{display:flex;align-items:center;gap:5px;min-height:64px;padding:11px 13px;border-top:1px solid var(--border)}footer button{display:grid;place-items:center;flex:0 0 auto;width:34px;height:34px;border:0;border-radius:10px;color:var(--text-secondary);background:transparent}footer button:hover{color:var(--primary-dark);background:var(--primary-extra-light)}footer input{min-width:0;flex:1;min-height:35px;padding:0 7px;border:0;outline:0;color:var(--text-main);background:transparent;font-size:11px}footer .send{color:#fff;background:var(--primary)}footer .send:hover{color:#fff;background:var(--primary-dark)}.chat-empty{display:grid;place-items:center}.modal-copy{margin:0 0 14px;color:var(--text-secondary);font-size:11px;line-height:1.5}.contact-search{margin:0 0 10px}.contact-list{display:grid;max-height:310px;overflow-y:auto}.contact-row{display:flex;align-items:center;gap:9px;width:100%;padding:10px 4px;border:0;border-top:1px solid var(--border);color:var(--text-main);background:#fff;text-align:left}.contact-row:hover{background:var(--primary-extra-light)}.contact-row b,.contact-row small{display:block}.contact-row b{font-size:11px}.contact-row small{margin-top:3px;color:var(--text-secondary);font-size:9px}@media(max-width:930px){.chat-shell{grid-template-columns:235px minmax(320px,1fr)}}@media(max-width:600px){.chat-page{margin:0 -13px}.chat-page>.page-heading{padding:0 13px}.chat-shell{grid-template-columns:1fr;min-height:640px;border-right:0;border-left:0;border-radius:0}.dialogs{max-height:194px;border-right:0;border-bottom:1px solid var(--border)}.dialog-list{display:flex;overflow-x:auto}.dialog{min-width:205px}.dialog.active::before{inset:auto 0 0;width:auto;height:3px}.conversation{min-height:446px}.message-area{min-height:280px}.conversation>header{padding:0 13px}}
</style>
