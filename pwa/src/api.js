import io from 'socket.io-client';

const socket = io();
socket.on('connect', () => {
  console.log('SocketIO connection established')
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
  const unsubscribe = () => {
    socket.off('hwdata', callback);
  };
  return unsubscribe;
}

export { sendMsg, onHwData };
