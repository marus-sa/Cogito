<script setup>
import { computed, ref } from 'vue'
import { FileText, Image, Info, Paperclip, Search, Send, Smile, X } from 'lucide-vue-next'
import { dialogs } from '../data/mockData'
import { useMessagesStore } from '../stores/messages'
import { useAuthStore } from '../stores/auth'
import UserAvatar from '../components/UserAvatar.vue'
import EmptyState from '../components/EmptyState.vue'

const messagesStore = useMessagesStore()
const auth = useAuthStore()
const activeId = ref(1)
const draft = ref('')
const search = ref('')
const infoOpen = ref(true)
const active = computed(() => dialogs.find((item) => item.id === activeId.value))
const messages = computed(() => messagesStore.messages.filter((item) => item.dialogId === activeId.value))
const filteredDialogs = computed(() => dialogs.filter((item) => item.name.toLowerCase().includes(search.value.toLowerCase())))
async function selectDialog(id) {
  activeId.value = id
  const dialog = dialogs.find((item) => item.id === id)
  if (dialog) dialog.unread = 0

  try {
    await messagesStore.loadMessages(id)
  } catch (error) {
    messagesStore.showToast(error.message, 'error')
  }
}

async function send() {
  const text = draft.value.trim()
  if (!text) return

  try {
    await messagesStore.send(activeId.value, text)
    draft.value = ''
  } catch (error) {
    messagesStore.showToast(error.message, 'error')
  }
}
function attach() { messagesStore.showToast('Файл прикреплён к сообщению') }
</script>
<template>
  <div class="page chat-page"><div class="page-heading"><div><h1>Чаты</h1><p>Обсуждайте обучение с командой проекта в одном месте.</p></div></div>
    <section class="chat-shell card"><aside class="dialogs"><div class="dialogs-head"><h2>Сообщения</h2><button aria-label="Новый диалог" @click="messagesStore.showToast('Выберите участника из списка проекта')">+</button></div><label class="dialog-search"><Search :size="15" /><input v-model="search" placeholder="Поиск диалогов" /></label><div class="dialog-list"><button v-for="dialog in filteredDialogs" :key="dialog.id" class="dialog" :class="{ active: activeId === dialog.id }" @click="selectDialog(dialog.id)"><UserAvatar :initials="dialog.initials" :color="dialog.color" :size="38" /><span class="dialog-text"><span><b>{{ dialog.name }}</b><em>{{ dialog.time }}</em></span><small>{{ dialog.role }} · {{ dialog.last }}</small></span><i v-if="dialog.unread">{{ dialog.unread }}</i></button><EmptyState v-if="!filteredDialogs.length" title="Диалогов не найдено" text="Попробуйте изменить запрос." /></div></aside>
      <main class="conversation"><header><div class="person"><UserAvatar :initials="active.initials" :color="active.color" :size="39" /><span><b>{{ active.name }}</b><small><i :class="{ online: active.online }"></i>{{ active.online ? 'В сети' : active.role }}</small></span></div><button class="info-button" :class="{ active: infoOpen }" aria-label="Информация о собеседнике" @click="infoOpen = !infoOpen"><Info :size="19" /></button></header><div v-if="messages.length" class="message-area"><div class="date-separator">Сегодня</div><div v-for="message in messages" :key="message.id" class="message" :class="message.sender"><p>{{ message.text }}</p><span>{{ message.time }} <i v-if="message.sender === 'me'">✓✓</i></span></div></div><EmptyState v-else title="Сообщений пока нет" text="Напишите первое сообщение этому участнику." /><footer><button aria-label="Прикрепить файл" @click="attach"><Paperclip :size="20" /></button><input v-model="draft" placeholder="Напишите сообщение…" @keydown.enter.prevent="send" /><button aria-label="Добавить эмодзи" @click="draft += ' 🙂'"><Smile :size="19" /></button><button class="send" aria-label="Отправить" @click="send"><Send :size="18" /></button></footer></main>
      <aside v-if="infoOpen" class="chat-info"><button class="close-info" aria-label="Закрыть информацию" @click="infoOpen = false"><X :size="17" /></button><UserAvatar :initials="active.initials" :color="active.color" :size="62" /><h3>{{ active.name }}</h3><p>{{ active.role }}</p><div class="info-details"><div><span>О собеседнике</span><b v-if="active.id === 1">11 класс · математика и информатика</b><b v-else>Участник проекта Light Hearts</b></div><div><span>Общий контекст</span><b>Математика · Анна Смирнова</b></div></div><div class="shared"><h4>Общие файлы</h4><button @click="messagesStore.showToast('Открыт файл «Карточка с заданиями.pdf»')"><FileText :size="16" /><span><b>Карточка с заданиями.pdf</b><small>Сегодня, 12:30</small></span></button><button @click="messagesStore.showToast('Открыто изображение')"><Image :size="16" /><span><b>Фото решения.jpg</b><small>Вчера, 18:12</small></span></button></div></aside>
    </section>
  </div>
</template>
<style scoped>
.chat-shell{display:grid;grid-template-columns:270px minmax(340px,1fr) 228px;min-height:590px;overflow:hidden}.dialogs,.chat-info{background:#fcfbfe}.dialogs{border-right:1px solid var(--border)}.dialogs-head{display:flex;align-items:center;justify-content:space-between;padding:18px 16px 12px}.dialogs-head h2{margin:0;font-size:15px}.dialogs-head button{display:grid;place-items:center;width:28px;height:28px;border:0;border-radius:8px;color:#fff;background:var(--primary);font-size:19px}.dialog-search{position:relative;display:flex;align-items:center;margin:0 13px 10px;color:var(--text-secondary)}.dialog-search svg{position:absolute;left:9px}.dialog-search input{width:100%;min-height:33px;padding:0 9px 0 31px;border:1px solid var(--border);border-radius:9px;outline:0;background:#fff;font-size:10px}.dialog-list{display:grid}.dialog{position:relative;display:flex;align-items:center;gap:9px;width:100%;padding:11px 13px;border:0;color:var(--text-main);background:transparent;text-align:left}.dialog:hover,.dialog.active{background:var(--primary-extra-light)}.dialog.active::before{position:absolute;left:0;width:3px;height:34px;content:'';background:var(--primary);border-radius:0 3px 3px 0}.dialog-text{min-width:0;flex:1}.dialog-text>span{display:flex;justify-content:space-between;gap:4px}.dialog b{display:block;overflow:hidden;font-size:11px;text-overflow:ellipsis;white-space:nowrap}.dialog em{color:var(--text-secondary);font-size:9px;font-style:normal}.dialog small{display:block;margin-top:3px;overflow:hidden;color:var(--text-secondary);font-size:9px;text-overflow:ellipsis;white-space:nowrap}.dialog>i{display:grid;place-items:center;min-width:16px;height:16px;padding:0 3px;color:#fff;background:var(--primary);border-radius:50%;font-size:8px;font-style:normal;font-weight:800}.conversation{display:flex;flex-direction:column;min-width:0;background:#fff}.conversation>header{display:flex;align-items:center;justify-content:space-between;min-height:65px;padding:0 18px;border-bottom:1px solid var(--border)}.person{display:flex;align-items:center;gap:9px}.person b,.person small{display:block}.person b{font-size:12px}.person small{margin-top:2px;color:var(--text-secondary);font-size:9px}.person small i{display:inline-block;width:6px;height:6px;margin:0 4px 1px 0;background:#b5adbE;border-radius:50%}.person small i.online{background:#73b792}.info-button{display:grid;place-items:center;width:33px;height:33px;border:0;border-radius:9px;color:var(--text-secondary);background:transparent}.info-button:hover,.info-button.active{color:var(--primary-dark);background:var(--primary-extra-light)}.message-area{display:flex;flex:1;flex-direction:column;gap:9px;padding:18px;overflow-y:auto;background:linear-gradient(145deg,#fff,#fdfbff)}.date-separator{align-self:center;padding:4px 8px;color:#948a9e;background:#f2eff5;border-radius:100px;font-size:9px}.message{max-width:73%;padding:9px 10px;border-radius:13px 13px 13px 3px;background:#f1edf7}.message.me{align-self:flex-end;border-radius:13px 13px 3px 13px;color:#fff;background:var(--primary)}.message p{margin:0;font-size:11px;line-height:1.55}.message>span{display:block;margin-top:4px;color:#93899e;font-size:8px;text-align:right}.message.me>span{color:#e9defa}.message.me i{margin-left:3px;color:#d6f3e1;font-style:normal}footer{display:flex;align-items:center;gap:5px;min-height:64px;padding:11px 13px;border-top:1px solid var(--border)}footer button{display:grid;place-items:center;flex:0 0 auto;width:34px;height:34px;border:0;border-radius:10px;color:var(--text-secondary);background:transparent}footer button:hover{color:var(--primary-dark);background:var(--primary-extra-light)}footer input{min-width:0;flex:1;min-height:35px;padding:0 7px;border:0;outline:0;color:var(--text-main);background:transparent;font-size:11px}footer .send{color:#fff;background:var(--primary)}footer .send:hover{color:#fff;background:var(--primary-dark)}.chat-info{position:relative;padding:24px 18px;border-left:1px solid var(--border);text-align:center}.close-info{position:absolute;top:10px;right:10px;display:grid;place-items:center;width:27px;height:27px;border:0;border-radius:8px;color:var(--text-secondary);background:transparent}.close-info:hover{background:var(--primary-extra-light)}.chat-info h3{margin:9px 0 3px;font-size:14px}.chat-info>p{margin:0;color:var(--text-secondary);font-size:10px}.info-details{display:grid;gap:11px;margin:23px 0;text-align:left}.info-details div{padding:10px;border-radius:10px;background:#f7f4fb}.info-details span,.info-details b{display:block}.info-details span{color:var(--text-secondary);font-size:9px}.info-details b{margin-top:4px;font-size:9px;line-height:1.45}.shared{padding-top:15px;border-top:1px solid var(--border);text-align:left}.shared h4{margin:0 0 9px;font-size:11px}.shared button{display:flex;align-items:center;gap:7px;width:100%;padding:8px 0;border:0;color:var(--primary-dark);background:transparent;text-align:left}.shared button span{min-width:0}.shared b,.shared small{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.shared b{font-size:9px}.shared small{margin-top:2px;color:var(--text-secondary);font-size:8px}@media(max-width:930px){.chat-shell{grid-template-columns:235px minmax(320px,1fr)}.chat-info{display:none}}@media(max-width:600px){.chat-page{margin:0 -13px}.chat-page>.page-heading{padding:0 13px}.chat-shell{grid-template-columns:1fr;min-height:640px;border-right:0;border-left:0;border-radius:0}.dialogs{max-height:194px;border-right:0;border-bottom:1px solid var(--border)}.dialog-list{display:flex;overflow-x:auto}.dialog{min-width:205px}.dialog.active::before{inset:auto 0 0;width:auto;height:3px}.conversation{min-height:446px}.message-area{min-height:280px}.conversation>header{padding:0 13px}}
</style>
