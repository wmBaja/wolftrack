import io from 'socket.io-client';

const socket = io();
socket.on('connect', function() {
  console.log('SocketIO connection established')
});

socket.on('hwdata', (data) => {
  console.log('Received hardware data');
  console.log(data);
});

socket.on('message', (data) => {
  console.log('Received general message');
  console.log(data);
})

function sendMsg() {
  socket.emit('blah', Math.random());
}

function onHwData(callback) {
  socket.on('hwdata', callback);
}

export { sendMsg, onHwData };
