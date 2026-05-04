// Sample data
const contacts = [
  {
    id: 1,
    name: 'Alice',
    messages: [
      { sender: 'them', text: 'Hey, how are you?' },
      { sender: 'me', text: 'I am good, thanks! How about you?' },
      { sender: 'them', text: 'Doing great, thanks!' },
    ],
  },
  {
    id: 2,
    name: 'Bob',
    messages: [
      { sender: 'them', text: 'Did you finish the report?' },
      { sender: 'me', text: 'Almost done, will send it soon.' },
    ],
  },
  {
    id: 3,
    name: 'Charlie',
    messages: [],
  },
];

let activeContactId = null;

const contactListEl = document.getElementById('contactList');
const chatHeaderEl = document.getElementById('chatHeader');
const messagesContainerEl = document.getElementById('messagesContainer');
const messageInputEl = document.getElementById('messageInput');
const sendBtnEl = document.getElementById('sendBtn');

function renderContactList() {
  contactListEl.innerHTML = '';
  contacts.forEach((c) => {
    const li = document.createElement('li');
    li.textContent = c.name;
    li.dataset.id = c.id;
    if (c.id === activeContactId) li.classList.add('active');
    li.addEventListener('click', () => selectContact(c.id));
    contactListEl.appendChild(li);
  });
}

function selectContact(id) {
  activeContactId = id;
  renderContactList();
  const contact = contacts.find((c) => c.id === id);
  chatHeaderEl.innerHTML = `<h3>${contact.name}</h3>`;
  renderMessages();
}

function renderMessages() {
  messagesContainerEl.innerHTML = '';
  const contact = contacts.find((c) => c.id === activeContactId);
  if (!contact) return;
  contact.messages.forEach((msg) => {
    const div = document.createElement('div');
    div.className = `message ${msg.sender === 'me' ? 'sent' : 'received'}`;
    div.textContent = msg.text;
    messagesContainerEl.appendChild(div);
  });
  messagesContainerEl.scrollTop = messagesContainerEl.scrollHeight;
}

function sendMessage() {
  const text = messageInputEl.value.trim();
  if (!text || activeContactId === null) return;
  const contact = contacts.find((c) => c.id === activeContactId);
  contact.messages.push({ sender: 'me', text });
  messageInputEl.value = '';
  renderMessages();
}

sendBtnEl.addEventListener('click', sendMessage);
messageInputEl.addEventListener('keypress', (e) => {
  if (e.key === 'Enter') sendMessage();
});

// Initialize with first contact selected
if (contacts.length > 0) selectContact(contacts[0].id);
