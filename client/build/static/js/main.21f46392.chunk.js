(window.webpackJsonp=window.webpackJsonp||[]).push([[0],{31:function(e,n,a){e.exports=a(68)},36:function(e,n,a){},37:function(e,n,a){},64:function(e,n){},67:function(e,n,a){},68:function(e,n,a){"use strict";a.r(n);var t=a(0),o=a.n(t),c=a(27),i=a.n(c),r=(a(36),a(30)),s=a(29),l=(a(37),a(28)),u=a.n(l)()();function d(){u.emit("blah",Math.random())}u.on("connect",function(){console.log("SocketIO connection established")}),u.on("message",function(e){console.log("Received general message"),console.log(e)});a(67);var m=function(e){var n=(100*e.data.fuelData.remainingPercentage).toPrecision(2),a=34.56783.toPrecision(2);return o.a.createElement("div",{className:"Dashboard"},o.a.createElement("button",{onClick:d,className:"Message"},"Send a message"),o.a.createElement("div",{className:"Fuel"},n),o.a.createElement("div",{className:"Speed"},a))},f={fuelData:{remainingPercentage:0,remainingLiters:0,remainingLitersEMA:0},gpsData:{latitude:0,longitude:0,speed:0,trackAngle:0}};var g=function(){var e=Object(t.useState)(f),n=Object(s.a)(e,2),a=n[0],c=n[1];return Object(t.useEffect)(function(){var e;return e=function(e){"fuel_data"===e.type&&(console.log("Updating fuel data",e.value),c(function(n){return Object(r.a)({},n,{fuelData:e.value})}))},u.on("hwdata",e),function(){u.off("hwdata",e)}},[]),o.a.createElement("div",{className:"App"},o.a.createElement(m,{data:a}))};Boolean("localhost"===window.location.hostname||"[::1]"===window.location.hostname||window.location.hostname.match(/^127(?:\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)){3}$/));i.a.render(o.a.createElement(g,null),document.getElementById("root")),"serviceWorker"in navigator&&navigator.serviceWorker.ready.then(function(e){e.unregister()})}},[[31,1,2]]]);
//# sourceMappingURL=main.21f46392.chunk.js.map