import require$$0 from "os";
import require$$2 from "events";
import require$$0$1 from "buffer";
import require$$1 from "dgram";
function _mergeNamespaces(n, m) {
  for (var i = 0; i < m.length; i++) {
    const e = m[i];
    if (typeof e !== "string" && !Array.isArray(e)) {
      for (const k in e) {
        if (k !== "default" && !(k in n)) {
          const d = Object.getOwnPropertyDescriptor(e, k);
          if (d) {
            Object.defineProperty(n, k, d.get ? d : {
              enumerable: true,
              get: () => e[k]
            });
          }
        }
      }
    }
  }
  return Object.freeze(Object.defineProperty(n, Symbol.toStringTag, { value: "Module" }));
}
function getDefaultExportFromCjs(x) {
  return x && x.__esModule && Object.prototype.hasOwnProperty.call(x, "default") ? x["default"] : x;
}
var dist = {};
var registry = {};
var dnsEqual = {};
var hasRequiredDnsEqual;
function requireDnsEqual() {
  if (hasRequiredDnsEqual) return dnsEqual;
  hasRequiredDnsEqual = 1;
  Object.defineProperty(dnsEqual, "__esModule", { value: true });
  dnsEqual.default = dnsEqual$1;
  const capitalLetterRegex = /[A-Z]/g;
  function toLowerCase(input) {
    return input.toLowerCase();
  }
  function dnsEqual$1(a, b) {
    const aFormatted = a.replace(capitalLetterRegex, toLowerCase);
    const bFormatted = b.replace(capitalLetterRegex, toLowerCase);
    return aFormatted === bFormatted;
  }
  return dnsEqual;
}
var service = {};
var dnsTxt = {};
var hasRequiredDnsTxt;
function requireDnsTxt() {
  if (hasRequiredDnsTxt) return dnsTxt;
  hasRequiredDnsTxt = 1;
  Object.defineProperty(dnsTxt, "__esModule", { value: true });
  dnsTxt.DnsTxt = void 0;
  class DnsTxt {
    constructor(opts = {}) {
      this.binary = opts ? opts.binary : false;
    }
    encode(data = {}) {
      return Object.entries(data).map(([key, value]) => {
        let item = `${key}=${value}`;
        return Buffer.from(item);
      });
    }
    decode(buffer) {
      var data = {};
      try {
        let format = buffer.toString();
        let parts = format.split(/=(.+)/);
        let key = parts[0];
        let value = parts[1];
        data[key] = value;
      } catch (_) {
      }
      return data;
    }
    decodeAll(buffer) {
      return buffer.filter((i) => i.length > 1).map((i) => this.decode(i)).reduce((prev, curr) => {
        var obj = prev;
        let [key] = Object.keys(curr);
        let [value] = Object.values(curr);
        obj[key] = value;
        return obj;
      }, {});
    }
  }
  dnsTxt.DnsTxt = DnsTxt;
  dnsTxt.default = DnsTxt;
  return dnsTxt;
}
var serviceTypes = {};
var hasRequiredServiceTypes;
function requireServiceTypes() {
  if (hasRequiredServiceTypes) return serviceTypes;
  hasRequiredServiceTypes = 1;
  Object.defineProperty(serviceTypes, "__esModule", { value: true });
  serviceTypes.toType = serviceTypes.toString = void 0;
  const Prefix = (name) => {
    return "_" + name;
  };
  const AllowedProp = (key) => {
    let keys = ["name", "protocol", "subtype"];
    return keys.includes(key);
  };
  const toString = (data) => {
    let formatted = {
      name: data.name,
      protocol: data.protocol,
      subtype: data.subtype
    };
    let entries = Object.entries(formatted);
    return entries.filter(([key, val]) => AllowedProp(key) && val !== void 0).reduce((prev, [key, val]) => {
      switch (typeof val) {
        case "object":
          val.map((i) => prev.push(Prefix(i)));
          break;
        default:
          prev.push(Prefix(val));
          break;
      }
      return prev;
    }, []).join(".");
  };
  serviceTypes.toString = toString;
  const toType = (string) => {
    let parts = string.split(".");
    let subtype;
    for (let i in parts) {
      if (parts[i][0] !== "_")
        continue;
      parts[i] = parts[i].slice(1);
    }
    if (parts.includes("sub")) {
      subtype = parts.shift();
      parts.shift();
    }
    return {
      name: parts.shift(),
      protocol: parts.shift() || null,
      subtype
    };
  };
  serviceTypes.toType = toType;
  return serviceTypes;
}
var hasRequiredService;
function requireService() {
  if (hasRequiredService) return service;
  hasRequiredService = 1;
  var __importDefault = service && service.__importDefault || function(mod) {
    return mod && mod.__esModule ? mod : { "default": mod };
  };
  Object.defineProperty(service, "__esModule", { value: true });
  service.Service = void 0;
  const os_1 = __importDefault(require$$0);
  const dns_txt_1 = __importDefault(requireDnsTxt());
  const events_1 = require$$2;
  const service_types_1 = requireServiceTypes();
  const TLD = ".local";
  class Service extends events_1.EventEmitter {
    constructor(config) {
      super();
      this.probe = true;
      this.published = false;
      this.activated = false;
      this.destroyed = false;
      this.txtService = new dns_txt_1.default();
      if (!config.name)
        throw new Error("ServiceConfig requires `name` property to be set");
      if (!config.type)
        throw new Error("ServiceConfig requires `type` property to be set");
      if (!config.port)
        throw new Error("ServiceConfig requires `port` property to be set");
      this.name = config.name.split(".").join("-");
      this.protocol = config.protocol || "tcp";
      this.type = (0, service_types_1.toString)({ name: config.type, protocol: this.protocol });
      this.port = config.port;
      this.host = config.host || os_1.default.hostname();
      this.fqdn = `${this.name}.${this.type}${TLD}`;
      this.txt = config.txt;
      this.subtypes = config.subtypes;
      this.disableIPv6 = !!config.disableIPv6;
    }
    records() {
      var records = [this.RecordPTR(this), this.RecordSRV(this), this.RecordTXT(this)];
      for (let subtype of this.subtypes || []) {
        records.push(this.RecordSubtypePTR(this, subtype));
      }
      let ifaces = Object.values(os_1.default.networkInterfaces());
      for (let iface of ifaces) {
        let addrs = iface;
        for (let addr of addrs) {
          if (addr.internal || addr.mac === "00:00:00:00:00:00")
            continue;
          switch (addr.family) {
            case "IPv4":
              records.push(this.RecordA(this, addr.address));
              break;
            case "IPv6":
              if (this.disableIPv6)
                break;
              records.push(this.RecordAAAA(this, addr.address));
              break;
          }
        }
      }
      return records;
    }
    RecordPTR(service2) {
      return {
        name: `${service2.type}${TLD}`,
        type: "PTR",
        ttl: 28800,
        data: service2.fqdn
      };
    }
    RecordSubtypePTR(service2, subtype) {
      return {
        name: `_${subtype}._sub.${service2.type}${TLD}`,
        type: "PTR",
        ttl: 28800,
        data: `${service2.name}.${service2.type}${TLD}`
      };
    }
    RecordSRV(service2) {
      return {
        name: service2.fqdn,
        type: "SRV",
        ttl: 120,
        data: {
          port: service2.port,
          target: service2.host
        }
      };
    }
    RecordTXT(service2) {
      return {
        name: service2.fqdn,
        type: "TXT",
        ttl: 4500,
        data: this.txtService.encode(service2.txt)
      };
    }
    RecordA(service2, ip) {
      return {
        name: service2.host,
        type: "A",
        ttl: 120,
        data: ip
      };
    }
    RecordAAAA(service2, ip) {
      return {
        name: service2.host,
        type: "AAAA",
        ttl: 120,
        data: ip
      };
    }
  }
  service.Service = Service;
  service.default = Service;
  return service;
}
var hasRequiredRegistry;
function requireRegistry() {
  if (hasRequiredRegistry) return registry;
  hasRequiredRegistry = 1;
  var __importDefault = registry && registry.__importDefault || function(mod) {
    return mod && mod.__esModule ? mod : { "default": mod };
  };
  Object.defineProperty(registry, "__esModule", { value: true });
  registry.Registry = void 0;
  const dns_equal_1 = __importDefault(requireDnsEqual());
  const service_1 = __importDefault(requireService());
  const REANNOUNCE_MAX_MS = 60 * 60 * 1e3;
  const REANNOUNCE_FACTOR = 3;
  const noop = function() {
  };
  class Registry {
    constructor(server) {
      this.services = [];
      this.server = server;
    }
    publish(config) {
      function start(service3, registry2, opts) {
        if (service3.activated)
          return;
        service3.activated = true;
        registry2.services.push(service3);
        if (!(service3 instanceof service_1.default))
          return;
        if (opts === null || opts === void 0 ? void 0 : opts.probe) {
          registry2.probe(registry2.server.mdns, service3, (exists) => {
            if (exists) {
              if (service3.stop !== void 0)
                service3.stop();
              console.log(new Error("Service name is already in use on the network"));
              return;
            }
            registry2.announce(registry2.server, service3);
          });
        } else {
          registry2.announce(registry2.server, service3);
        }
      }
      function stop(service3, registry2, callback) {
        if (!callback)
          callback = noop;
        if (!service3.activated)
          return process.nextTick(callback);
        if (!(service3 instanceof service_1.default))
          return process.nextTick(callback);
        registry2.teardown(registry2.server, service3, callback);
        const index2 = registry2.services.indexOf(service3);
        if (index2 !== -1)
          registry2.services.splice(index2, 1);
      }
      const service2 = new service_1.default(config);
      service2.start = start.bind(null, service2, this);
      service2.stop = stop.bind(null, service2, this);
      service2.start({ probe: config.probe !== false });
      return service2;
    }
    unpublishAll(callback) {
      this.teardown(this.server, this.services, callback);
      this.services = [];
    }
    destroy() {
      this.services.map((service2) => service2.destroyed = true);
    }
    probe(mdns, service2, callback) {
      var sent = false;
      var retries = 0;
      var timer;
      const send = () => {
        if (!service2.activated || service2.destroyed)
          return;
        mdns.query(service2.fqdn, "ANY", function() {
          sent = true;
          timer = setTimeout(++retries < 3 ? send : done, 250);
          timer.unref();
        });
      };
      const onresponse = (packet) => {
        if (!sent)
          return;
        if (packet.answers.some(matchRR) || packet.additionals.some(matchRR))
          done(true);
      };
      const matchRR = (rr) => {
        return (0, dns_equal_1.default)(rr.name, service2.fqdn);
      };
      const done = (exists) => {
        mdns.removeListener("response", onresponse);
        clearTimeout(timer);
        callback(!!exists);
      };
      mdns.on("response", onresponse);
      setTimeout(send, Math.random() * 250);
    }
    announce(server, service2) {
      var delay = 1e3;
      var packet = service2.records();
      server.register(packet);
      const broadcast = () => {
        if (!service2.activated || service2.destroyed)
          return;
        server.mdns.respond(packet, function() {
          if (!service2.published) {
            service2.activated = true;
            service2.published = true;
            service2.emit("up");
          }
          delay = delay * REANNOUNCE_FACTOR;
          if (delay < REANNOUNCE_MAX_MS && !service2.destroyed) {
            setTimeout(broadcast, delay).unref();
          }
        });
      };
      broadcast();
    }
    teardown(server, services, callback) {
      if (!Array.isArray(services))
        services = [services];
      services = services.filter((service2) => service2.activated);
      var records = services.flatMap(function(service2) {
        service2.activated = false;
        var records2 = service2.records();
        records2.forEach((record) => {
          record.ttl = 0;
        });
        return records2;
      });
      if (records.length === 0)
        return callback && process.nextTick(callback);
      server.unregister(records);
      server.mdns.respond(records, function() {
        services.forEach(function(service2) {
          service2.published = false;
        });
        if (typeof callback === "function") {
          callback.apply(null, arguments);
        }
      });
    }
  }
  registry.Registry = Registry;
  registry.default = Registry;
  return registry;
}
var mdnsServer = {};
var dnsPacket = {};
var types = {};
var hasRequiredTypes;
function requireTypes() {
  if (hasRequiredTypes) return types;
  hasRequiredTypes = 1;
  types.toString = function(type) {
    switch (type) {
      case 1:
        return "A";
      case 10:
        return "NULL";
      case 28:
        return "AAAA";
      case 18:
        return "AFSDB";
      case 42:
        return "APL";
      case 257:
        return "CAA";
      case 60:
        return "CDNSKEY";
      case 59:
        return "CDS";
      case 37:
        return "CERT";
      case 5:
        return "CNAME";
      case 49:
        return "DHCID";
      case 32769:
        return "DLV";
      case 39:
        return "DNAME";
      case 48:
        return "DNSKEY";
      case 43:
        return "DS";
      case 55:
        return "HIP";
      case 13:
        return "HINFO";
      case 45:
        return "IPSECKEY";
      case 25:
        return "KEY";
      case 36:
        return "KX";
      case 29:
        return "LOC";
      case 15:
        return "MX";
      case 35:
        return "NAPTR";
      case 2:
        return "NS";
      case 47:
        return "NSEC";
      case 50:
        return "NSEC3";
      case 51:
        return "NSEC3PARAM";
      case 12:
        return "PTR";
      case 46:
        return "RRSIG";
      case 17:
        return "RP";
      case 24:
        return "SIG";
      case 6:
        return "SOA";
      case 99:
        return "SPF";
      case 33:
        return "SRV";
      case 44:
        return "SSHFP";
      case 32768:
        return "TA";
      case 249:
        return "TKEY";
      case 52:
        return "TLSA";
      case 250:
        return "TSIG";
      case 16:
        return "TXT";
      case 252:
        return "AXFR";
      case 251:
        return "IXFR";
      case 41:
        return "OPT";
      case 255:
        return "ANY";
    }
    return "UNKNOWN_" + type;
  };
  types.toType = function(name) {
    switch (name.toUpperCase()) {
      case "A":
        return 1;
      case "NULL":
        return 10;
      case "AAAA":
        return 28;
      case "AFSDB":
        return 18;
      case "APL":
        return 42;
      case "CAA":
        return 257;
      case "CDNSKEY":
        return 60;
      case "CDS":
        return 59;
      case "CERT":
        return 37;
      case "CNAME":
        return 5;
      case "DHCID":
        return 49;
      case "DLV":
        return 32769;
      case "DNAME":
        return 39;
      case "DNSKEY":
        return 48;
      case "DS":
        return 43;
      case "HIP":
        return 55;
      case "HINFO":
        return 13;
      case "IPSECKEY":
        return 45;
      case "KEY":
        return 25;
      case "KX":
        return 36;
      case "LOC":
        return 29;
      case "MX":
        return 15;
      case "NAPTR":
        return 35;
      case "NS":
        return 2;
      case "NSEC":
        return 47;
      case "NSEC3":
        return 50;
      case "NSEC3PARAM":
        return 51;
      case "PTR":
        return 12;
      case "RRSIG":
        return 46;
      case "RP":
        return 17;
      case "SIG":
        return 24;
      case "SOA":
        return 6;
      case "SPF":
        return 99;
      case "SRV":
        return 33;
      case "SSHFP":
        return 44;
      case "TA":
        return 32768;
      case "TKEY":
        return 249;
      case "TLSA":
        return 52;
      case "TSIG":
        return 250;
      case "TXT":
        return 16;
      case "AXFR":
        return 252;
      case "IXFR":
        return 251;
      case "OPT":
        return 41;
      case "ANY":
        return 255;
      case "*":
        return 255;
    }
    if (name.toUpperCase().startsWith("UNKNOWN_")) return parseInt(name.slice(8));
    return 0;
  };
  return types;
}
var rcodes = {};
var hasRequiredRcodes;
function requireRcodes() {
  if (hasRequiredRcodes) return rcodes;
  hasRequiredRcodes = 1;
  rcodes.toString = function(rcode) {
    switch (rcode) {
      case 0:
        return "NOERROR";
      case 1:
        return "FORMERR";
      case 2:
        return "SERVFAIL";
      case 3:
        return "NXDOMAIN";
      case 4:
        return "NOTIMP";
      case 5:
        return "REFUSED";
      case 6:
        return "YXDOMAIN";
      case 7:
        return "YXRRSET";
      case 8:
        return "NXRRSET";
      case 9:
        return "NOTAUTH";
      case 10:
        return "NOTZONE";
      case 11:
        return "RCODE_11";
      case 12:
        return "RCODE_12";
      case 13:
        return "RCODE_13";
      case 14:
        return "RCODE_14";
      case 15:
        return "RCODE_15";
    }
    return "RCODE_" + rcode;
  };
  rcodes.toRcode = function(code) {
    switch (code.toUpperCase()) {
      case "NOERROR":
        return 0;
      case "FORMERR":
        return 1;
      case "SERVFAIL":
        return 2;
      case "NXDOMAIN":
        return 3;
      case "NOTIMP":
        return 4;
      case "REFUSED":
        return 5;
      case "YXDOMAIN":
        return 6;
      case "YXRRSET":
        return 7;
      case "NXRRSET":
        return 8;
      case "NOTAUTH":
        return 9;
      case "NOTZONE":
        return 10;
      case "RCODE_11":
        return 11;
      case "RCODE_12":
        return 12;
      case "RCODE_13":
        return 13;
      case "RCODE_14":
        return 14;
      case "RCODE_15":
        return 15;
    }
    return 0;
  };
  return rcodes;
}
var opcodes = {};
var hasRequiredOpcodes;
function requireOpcodes() {
  if (hasRequiredOpcodes) return opcodes;
  hasRequiredOpcodes = 1;
  opcodes.toString = function(opcode) {
    switch (opcode) {
      case 0:
        return "QUERY";
      case 1:
        return "IQUERY";
      case 2:
        return "STATUS";
      case 3:
        return "OPCODE_3";
      case 4:
        return "NOTIFY";
      case 5:
        return "UPDATE";
      case 6:
        return "OPCODE_6";
      case 7:
        return "OPCODE_7";
      case 8:
        return "OPCODE_8";
      case 9:
        return "OPCODE_9";
      case 10:
        return "OPCODE_10";
      case 11:
        return "OPCODE_11";
      case 12:
        return "OPCODE_12";
      case 13:
        return "OPCODE_13";
      case 14:
        return "OPCODE_14";
      case 15:
        return "OPCODE_15";
    }
    return "OPCODE_" + opcode;
  };
  opcodes.toOpcode = function(code) {
    switch (code.toUpperCase()) {
      case "QUERY":
        return 0;
      case "IQUERY":
        return 1;
      case "STATUS":
        return 2;
      case "OPCODE_3":
        return 3;
      case "NOTIFY":
        return 4;
      case "UPDATE":
        return 5;
      case "OPCODE_6":
        return 6;
      case "OPCODE_7":
        return 7;
      case "OPCODE_8":
        return 8;
      case "OPCODE_9":
        return 9;
      case "OPCODE_10":
        return 10;
      case "OPCODE_11":
        return 11;
      case "OPCODE_12":
        return 12;
      case "OPCODE_13":
        return 13;
      case "OPCODE_14":
        return 14;
      case "OPCODE_15":
        return 15;
    }
    return 0;
  };
  return opcodes;
}
var classes = {};
var hasRequiredClasses;
function requireClasses() {
  if (hasRequiredClasses) return classes;
  hasRequiredClasses = 1;
  classes.toString = function(klass) {
    switch (klass) {
      case 1:
        return "IN";
      case 2:
        return "CS";
      case 3:
        return "CH";
      case 4:
        return "HS";
      case 255:
        return "ANY";
    }
    return "UNKNOWN_" + klass;
  };
  classes.toClass = function(name) {
    switch (name.toUpperCase()) {
      case "IN":
        return 1;
      case "CS":
        return 2;
      case "CH":
        return 3;
      case "HS":
        return 4;
      case "ANY":
        return 255;
    }
    return 0;
  };
  return classes;
}
var optioncodes = {};
var hasRequiredOptioncodes;
function requireOptioncodes() {
  if (hasRequiredOptioncodes) return optioncodes;
  hasRequiredOptioncodes = 1;
  optioncodes.toString = function(type) {
    switch (type) {
      // list at
      // https://www.iana.org/assignments/dns-parameters/dns-parameters.xhtml#dns-parameters-11
      case 1:
        return "LLQ";
      case 2:
        return "UL";
      case 3:
        return "NSID";
      case 5:
        return "DAU";
      case 6:
        return "DHU";
      case 7:
        return "N3U";
      case 8:
        return "CLIENT_SUBNET";
      case 9:
        return "EXPIRE";
      case 10:
        return "COOKIE";
      case 11:
        return "TCP_KEEPALIVE";
      case 12:
        return "PADDING";
      case 13:
        return "CHAIN";
      case 14:
        return "KEY_TAG";
      case 26946:
        return "DEVICEID";
    }
    if (type < 0) {
      return null;
    }
    return `OPTION_${type}`;
  };
  optioncodes.toCode = function(name) {
    if (typeof name === "number") {
      return name;
    }
    if (!name) {
      return -1;
    }
    switch (name.toUpperCase()) {
      case "OPTION_0":
        return 0;
      case "LLQ":
        return 1;
      case "UL":
        return 2;
      case "NSID":
        return 3;
      case "OPTION_4":
        return 4;
      case "DAU":
        return 5;
      case "DHU":
        return 6;
      case "N3U":
        return 7;
      case "CLIENT_SUBNET":
        return 8;
      case "EXPIRE":
        return 9;
      case "COOKIE":
        return 10;
      case "TCP_KEEPALIVE":
        return 11;
      case "PADDING":
        return 12;
      case "CHAIN":
        return 13;
      case "KEY_TAG":
        return 14;
      case "DEVICEID":
        return 26946;
      case "OPTION_65535":
        return 65535;
    }
    const m = name.match(/_(\d+)$/);
    if (m) {
      return parseInt(m[1], 10);
    }
    return -1;
  };
  return optioncodes;
}
var ipCodec = { exports: {} };
var hasRequiredIpCodec;
function requireIpCodec() {
  if (hasRequiredIpCodec) return ipCodec.exports;
  hasRequiredIpCodec = 1;
  (function(module, exports$1) {
    var ipCodec2 = (function(exports$12) {
      Object.defineProperty(exports$12, "__esModule", {
        value: true
      });
      exports$12.decode = decode;
      exports$12.encode = encode;
      exports$12.familyOf = familyOf;
      exports$12.name = void 0;
      exports$12.sizeOf = sizeOf;
      exports$12.v6 = exports$12.v4 = void 0;
      const v4Regex = /^(\d{1,3}\.){3,3}\d{1,3}$/;
      const v4Size = 4;
      const v6Regex = /^(::)?(((\d{1,3}\.){3}(\d{1,3}){1})?([0-9a-f]){0,4}:{0,2}){1,8}(::)?$/i;
      const v6Size = 16;
      const v4 = {
        name: "v4",
        size: v4Size,
        isFormat: (ip) => v4Regex.test(ip),
        encode(ip, buff, offset) {
          offset = ~~offset;
          buff = buff || new Uint8Array(offset + v4Size);
          const max = ip.length;
          let n = 0;
          for (let i = 0; i < max; ) {
            const c = ip.charCodeAt(i++);
            if (c === 46) {
              buff[offset++] = n;
              n = 0;
            } else {
              n = n * 10 + (c - 48);
            }
          }
          buff[offset] = n;
          return buff;
        },
        decode(buff, offset) {
          offset = ~~offset;
          return `${buff[offset++]}.${buff[offset++]}.${buff[offset++]}.${buff[offset]}`;
        }
      };
      exports$12.v4 = v4;
      const v6 = {
        name: "v6",
        size: v6Size,
        isFormat: (ip) => ip.length > 0 && v6Regex.test(ip),
        encode(ip, buff, offset) {
          offset = ~~offset;
          let end = offset + v6Size;
          let fill = -1;
          let hexN = 0;
          let decN = 0;
          let prevColon = true;
          let useDec = false;
          buff = buff || new Uint8Array(offset + v6Size);
          for (let i = 0; i < ip.length; i++) {
            let c = ip.charCodeAt(i);
            if (c === 58) {
              if (prevColon) {
                if (fill !== -1) {
                  if (offset < end) buff[offset] = 0;
                  if (offset < end - 1) buff[offset + 1] = 0;
                  offset += 2;
                } else if (offset < end) {
                  fill = offset;
                }
              } else {
                if (useDec === true) {
                  if (offset < end) buff[offset] = decN;
                  offset++;
                } else {
                  if (offset < end) buff[offset] = hexN >> 8;
                  if (offset < end - 1) buff[offset + 1] = hexN & 255;
                  offset += 2;
                }
                hexN = 0;
                decN = 0;
              }
              prevColon = true;
              useDec = false;
            } else if (c === 46) {
              if (offset < end) buff[offset] = decN;
              offset++;
              decN = 0;
              hexN = 0;
              prevColon = false;
              useDec = true;
            } else {
              prevColon = false;
              if (c >= 97) {
                c -= 87;
              } else if (c >= 65) {
                c -= 55;
              } else {
                c -= 48;
                decN = decN * 10 + c;
              }
              hexN = (hexN << 4) + c;
            }
          }
          if (prevColon === false) {
            if (useDec === true) {
              if (offset < end) buff[offset] = decN;
              offset++;
            } else {
              if (offset < end) buff[offset] = hexN >> 8;
              if (offset < end - 1) buff[offset + 1] = hexN & 255;
              offset += 2;
            }
          } else if (fill === 0) {
            if (offset < end) buff[offset] = 0;
            if (offset < end - 1) buff[offset + 1] = 0;
            offset += 2;
          } else if (fill !== -1) {
            offset += 2;
            for (let i = Math.min(offset - 1, end - 1); i >= fill + 2; i--) {
              buff[i] = buff[i - 2];
            }
            buff[fill] = 0;
            buff[fill + 1] = 0;
            fill = offset;
          }
          if (fill !== offset && fill !== -1) {
            if (offset > end - 2) {
              offset = end - 2;
            }
            while (end > fill) {
              buff[--end] = offset < end && offset > fill ? buff[--offset] : 0;
            }
          } else {
            while (offset < end) {
              buff[offset++] = 0;
            }
          }
          return buff;
        },
        decode(buff, offset) {
          offset = ~~offset;
          let result = "";
          for (let i = 0; i < v6Size; i += 2) {
            if (i !== 0) {
              result += ":";
            }
            result += (buff[offset + i] << 8 | buff[offset + i + 1]).toString(16);
          }
          return result.replace(/(^|:)0(:0)*:0(:|$)/, "$1::$3").replace(/:{3,4}/, "::");
        }
      };
      exports$12.v6 = v6;
      const name = "ip";
      exports$12.name = name;
      function sizeOf(ip) {
        if (v4.isFormat(ip)) return v4.size;
        if (v6.isFormat(ip)) return v6.size;
        throw Error(`Invalid ip address: ${ip}`);
      }
      function familyOf(string) {
        return sizeOf(string) === v4.size ? 1 : 2;
      }
      function encode(ip, buff, offset) {
        offset = ~~offset;
        const size = sizeOf(ip);
        if (typeof buff === "function") {
          buff = buff(offset + size);
        }
        if (size === v4.size) {
          return v4.encode(ip, buff, offset);
        }
        return v6.encode(ip, buff, offset);
      }
      function decode(buff, offset, length) {
        offset = ~~offset;
        length = length || buff.length - offset;
        if (length === v4.size) {
          return v4.decode(buff, offset, length);
        }
        if (length === v6.size) {
          return v6.decode(buff, offset, length);
        }
        throw Error(`Invalid buffer size needs to be ${v4.size} for v4 or ${v6.size} for v6.`);
      }
      return "default" in exports$12 ? exports$12.default : exports$12;
    })({});
    module.exports = ipCodec2;
  })(ipCodec);
  return ipCodec.exports;
}
var hasRequiredDnsPacket;
function requireDnsPacket() {
  if (hasRequiredDnsPacket) return dnsPacket;
  hasRequiredDnsPacket = 1;
  (function(exports$1) {
    const Buffer2 = require$$0$1.Buffer;
    const types2 = requireTypes();
    const rcodes2 = requireRcodes();
    const opcodes2 = requireOpcodes();
    const classes2 = requireClasses();
    const optioncodes2 = requireOptioncodes();
    const ip = requireIpCodec();
    const QUERY_FLAG = 0;
    const RESPONSE_FLAG = 1 << 15;
    const FLUSH_MASK = 1 << 15;
    const NOT_FLUSH_MASK = ~FLUSH_MASK;
    const QU_MASK = 1 << 15;
    const NOT_QU_MASK = ~QU_MASK;
    const name = exports$1.name = {};
    name.encode = function(str, buf, offset, { mail = false } = {}) {
      if (!buf) buf = Buffer2.alloc(name.encodingLength(str));
      if (!offset) offset = 0;
      const oldOffset = offset;
      const n = str.replace(/^\.|\.$/gm, "");
      if (n.length) {
        let list = [];
        if (mail) {
          let localPart = "";
          n.split(".").forEach((label) => {
            if (label.endsWith("\\")) {
              localPart += (localPart.length ? "." : "") + label.slice(0, -1);
            } else {
              if (list.length === 0 && localPart.length) {
                list.push(localPart + "." + label);
              } else {
                list.push(label);
              }
            }
          });
        } else {
          list = n.split(".");
        }
        for (let i = 0; i < list.length; i++) {
          const len = buf.write(list[i], offset + 1);
          buf[offset] = len;
          offset += len + 1;
        }
      }
      buf[offset++] = 0;
      name.encode.bytes = offset - oldOffset;
      return buf;
    };
    name.encode.bytes = 0;
    name.decode = function(buf, offset, { mail = false } = {}) {
      if (!offset) offset = 0;
      const list = [];
      let oldOffset = offset;
      let totalLength = 0;
      let consumedBytes = 0;
      let jumped = false;
      while (true) {
        if (offset >= buf.length) {
          throw new Error("Cannot decode name (buffer overflow)");
        }
        const len = buf[offset++];
        consumedBytes += jumped ? 0 : 1;
        if (len === 0) {
          break;
        } else if ((len & 192) === 0) {
          if (offset + len > buf.length) {
            throw new Error("Cannot decode name (buffer overflow)");
          }
          totalLength += len + 1;
          if (totalLength > 254) {
            throw new Error("Cannot decode name (name too long)");
          }
          let label = buf.toString("utf-8", offset, offset + len);
          if (mail) {
            label = label.replace(/\./g, "\\.");
          }
          list.push(label);
          offset += len;
          consumedBytes += jumped ? 0 : len;
        } else if ((len & 192) === 192) {
          if (offset + 1 > buf.length) {
            throw new Error("Cannot decode name (buffer overflow)");
          }
          const jumpOffset = buf.readUInt16BE(offset - 1) - 49152;
          if (jumpOffset >= oldOffset) {
            throw new Error("Cannot decode name (bad pointer)");
          }
          offset = jumpOffset;
          oldOffset = jumpOffset;
          consumedBytes += jumped ? 0 : 1;
          jumped = true;
        } else {
          throw new Error("Cannot decode name (bad label)");
        }
      }
      name.decode.bytes = consumedBytes;
      return list.length === 0 ? "." : list.join(".");
    };
    name.decode.bytes = 0;
    name.encodingLength = function(n) {
      if (n === "." || n === "..") return 1;
      return Buffer2.byteLength(n.replace(/^\.|\.$/gm, "")) + 2;
    };
    const string = {};
    string.encode = function(s, buf, offset) {
      if (!buf) buf = Buffer2.alloc(string.encodingLength(s));
      if (!offset) offset = 0;
      const len = buf.write(s, offset + 1);
      buf[offset] = len;
      string.encode.bytes = len + 1;
      return buf;
    };
    string.encode.bytes = 0;
    string.decode = function(buf, offset) {
      if (!offset) offset = 0;
      const len = buf[offset];
      const s = buf.toString("utf-8", offset + 1, offset + 1 + len);
      string.decode.bytes = len + 1;
      return s;
    };
    string.decode.bytes = 0;
    string.encodingLength = function(s) {
      return Buffer2.byteLength(s) + 1;
    };
    const header = {};
    header.encode = function(h, buf, offset) {
      if (!buf) buf = header.encodingLength(h);
      if (!offset) offset = 0;
      const flags = (h.flags || 0) & 32767;
      const type = h.type === "response" ? RESPONSE_FLAG : QUERY_FLAG;
      buf.writeUInt16BE(h.id || 0, offset);
      buf.writeUInt16BE(flags | type, offset + 2);
      buf.writeUInt16BE(h.questions.length, offset + 4);
      buf.writeUInt16BE(h.answers.length, offset + 6);
      buf.writeUInt16BE(h.authorities.length, offset + 8);
      buf.writeUInt16BE(h.additionals.length, offset + 10);
      return buf;
    };
    header.encode.bytes = 12;
    header.decode = function(buf, offset) {
      if (!offset) offset = 0;
      if (buf.length < 12) throw new Error("Header must be 12 bytes");
      const flags = buf.readUInt16BE(offset + 2);
      return {
        id: buf.readUInt16BE(offset),
        type: flags & RESPONSE_FLAG ? "response" : "query",
        flags: flags & 32767,
        flag_qr: (flags >> 15 & 1) === 1,
        opcode: opcodes2.toString(flags >> 11 & 15),
        flag_aa: (flags >> 10 & 1) === 1,
        flag_tc: (flags >> 9 & 1) === 1,
        flag_rd: (flags >> 8 & 1) === 1,
        flag_ra: (flags >> 7 & 1) === 1,
        flag_z: (flags >> 6 & 1) === 1,
        flag_ad: (flags >> 5 & 1) === 1,
        flag_cd: (flags >> 4 & 1) === 1,
        rcode: rcodes2.toString(flags & 15),
        questions: new Array(buf.readUInt16BE(offset + 4)),
        answers: new Array(buf.readUInt16BE(offset + 6)),
        authorities: new Array(buf.readUInt16BE(offset + 8)),
        additionals: new Array(buf.readUInt16BE(offset + 10))
      };
    };
    header.decode.bytes = 12;
    header.encodingLength = function() {
      return 12;
    };
    const runknown = exports$1.unknown = {};
    runknown.encode = function(data, buf, offset) {
      if (!buf) buf = Buffer2.alloc(runknown.encodingLength(data));
      if (!offset) offset = 0;
      buf.writeUInt16BE(data.length, offset);
      data.copy(buf, offset + 2);
      runknown.encode.bytes = data.length + 2;
      return buf;
    };
    runknown.encode.bytes = 0;
    runknown.decode = function(buf, offset) {
      if (!offset) offset = 0;
      const len = buf.readUInt16BE(offset);
      const data = buf.slice(offset + 2, offset + 2 + len);
      runknown.decode.bytes = len + 2;
      return data;
    };
    runknown.decode.bytes = 0;
    runknown.encodingLength = function(data) {
      return data.length + 2;
    };
    const rns = exports$1.ns = {};
    rns.encode = function(data, buf, offset) {
      if (!buf) buf = Buffer2.alloc(rns.encodingLength(data));
      if (!offset) offset = 0;
      name.encode(data, buf, offset + 2);
      buf.writeUInt16BE(name.encode.bytes, offset);
      rns.encode.bytes = name.encode.bytes + 2;
      return buf;
    };
    rns.encode.bytes = 0;
    rns.decode = function(buf, offset) {
      if (!offset) offset = 0;
      const len = buf.readUInt16BE(offset);
      const dd = name.decode(buf, offset + 2);
      rns.decode.bytes = len + 2;
      return dd;
    };
    rns.decode.bytes = 0;
    rns.encodingLength = function(data) {
      return name.encodingLength(data) + 2;
    };
    const rsoa = exports$1.soa = {};
    rsoa.encode = function(data, buf, offset) {
      if (!buf) buf = Buffer2.alloc(rsoa.encodingLength(data));
      if (!offset) offset = 0;
      const oldOffset = offset;
      offset += 2;
      name.encode(data.mname, buf, offset);
      offset += name.encode.bytes;
      name.encode(data.rname, buf, offset, { mail: true });
      offset += name.encode.bytes;
      buf.writeUInt32BE(data.serial || 0, offset);
      offset += 4;
      buf.writeUInt32BE(data.refresh || 0, offset);
      offset += 4;
      buf.writeUInt32BE(data.retry || 0, offset);
      offset += 4;
      buf.writeUInt32BE(data.expire || 0, offset);
      offset += 4;
      buf.writeUInt32BE(data.minimum || 0, offset);
      offset += 4;
      buf.writeUInt16BE(offset - oldOffset - 2, oldOffset);
      rsoa.encode.bytes = offset - oldOffset;
      return buf;
    };
    rsoa.encode.bytes = 0;
    rsoa.decode = function(buf, offset) {
      if (!offset) offset = 0;
      const oldOffset = offset;
      const data = {};
      offset += 2;
      data.mname = name.decode(buf, offset);
      offset += name.decode.bytes;
      data.rname = name.decode(buf, offset, { mail: true });
      offset += name.decode.bytes;
      data.serial = buf.readUInt32BE(offset);
      offset += 4;
      data.refresh = buf.readUInt32BE(offset);
      offset += 4;
      data.retry = buf.readUInt32BE(offset);
      offset += 4;
      data.expire = buf.readUInt32BE(offset);
      offset += 4;
      data.minimum = buf.readUInt32BE(offset);
      offset += 4;
      rsoa.decode.bytes = offset - oldOffset;
      return data;
    };
    rsoa.decode.bytes = 0;
    rsoa.encodingLength = function(data) {
      return 22 + name.encodingLength(data.mname) + name.encodingLength(data.rname);
    };
    const rtxt = exports$1.txt = {};
    rtxt.encode = function(data, buf, offset) {
      if (!Array.isArray(data)) data = [data];
      for (let i = 0; i < data.length; i++) {
        if (typeof data[i] === "string") {
          data[i] = Buffer2.from(data[i]);
        }
        if (!Buffer2.isBuffer(data[i])) {
          throw new Error("Must be a Buffer");
        }
      }
      if (!buf) buf = Buffer2.alloc(rtxt.encodingLength(data));
      if (!offset) offset = 0;
      const oldOffset = offset;
      offset += 2;
      data.forEach(function(d) {
        buf[offset++] = d.length;
        d.copy(buf, offset, 0, d.length);
        offset += d.length;
      });
      buf.writeUInt16BE(offset - oldOffset - 2, oldOffset);
      rtxt.encode.bytes = offset - oldOffset;
      return buf;
    };
    rtxt.encode.bytes = 0;
    rtxt.decode = function(buf, offset) {
      if (!offset) offset = 0;
      const oldOffset = offset;
      let remaining = buf.readUInt16BE(offset);
      offset += 2;
      let data = [];
      while (remaining > 0) {
        const len = buf[offset++];
        --remaining;
        if (remaining < len) {
          throw new Error("Buffer overflow");
        }
        data.push(buf.slice(offset, offset + len));
        offset += len;
        remaining -= len;
      }
      rtxt.decode.bytes = offset - oldOffset;
      return data;
    };
    rtxt.decode.bytes = 0;
    rtxt.encodingLength = function(data) {
      if (!Array.isArray(data)) data = [data];
      let length = 2;
      data.forEach(function(buf) {
        if (typeof buf === "string") {
          length += Buffer2.byteLength(buf) + 1;
        } else {
          length += buf.length + 1;
        }
      });
      return length;
    };
    const rnull = exports$1.null = {};
    rnull.encode = function(data, buf, offset) {
      if (!buf) buf = Buffer2.alloc(rnull.encodingLength(data));
      if (!offset) offset = 0;
      if (typeof data === "string") data = Buffer2.from(data);
      if (!data) data = Buffer2.alloc(0);
      const oldOffset = offset;
      offset += 2;
      const len = data.length;
      data.copy(buf, offset, 0, len);
      offset += len;
      buf.writeUInt16BE(offset - oldOffset - 2, oldOffset);
      rnull.encode.bytes = offset - oldOffset;
      return buf;
    };
    rnull.encode.bytes = 0;
    rnull.decode = function(buf, offset) {
      if (!offset) offset = 0;
      const oldOffset = offset;
      const len = buf.readUInt16BE(offset);
      offset += 2;
      const data = buf.slice(offset, offset + len);
      offset += len;
      rnull.decode.bytes = offset - oldOffset;
      return data;
    };
    rnull.decode.bytes = 0;
    rnull.encodingLength = function(data) {
      if (!data) return 2;
      return (Buffer2.isBuffer(data) ? data.length : Buffer2.byteLength(data)) + 2;
    };
    const rhinfo = exports$1.hinfo = {};
    rhinfo.encode = function(data, buf, offset) {
      if (!buf) buf = Buffer2.alloc(rhinfo.encodingLength(data));
      if (!offset) offset = 0;
      const oldOffset = offset;
      offset += 2;
      string.encode(data.cpu, buf, offset);
      offset += string.encode.bytes;
      string.encode(data.os, buf, offset);
      offset += string.encode.bytes;
      buf.writeUInt16BE(offset - oldOffset - 2, oldOffset);
      rhinfo.encode.bytes = offset - oldOffset;
      return buf;
    };
    rhinfo.encode.bytes = 0;
    rhinfo.decode = function(buf, offset) {
      if (!offset) offset = 0;
      const oldOffset = offset;
      const data = {};
      offset += 2;
      data.cpu = string.decode(buf, offset);
      offset += string.decode.bytes;
      data.os = string.decode(buf, offset);
      offset += string.decode.bytes;
      rhinfo.decode.bytes = offset - oldOffset;
      return data;
    };
    rhinfo.decode.bytes = 0;
    rhinfo.encodingLength = function(data) {
      return string.encodingLength(data.cpu) + string.encodingLength(data.os) + 2;
    };
    const rptr = exports$1.ptr = {};
    const rcname = exports$1.cname = rptr;
    const rdname = exports$1.dname = rptr;
    rptr.encode = function(data, buf, offset) {
      if (!buf) buf = Buffer2.alloc(rptr.encodingLength(data));
      if (!offset) offset = 0;
      name.encode(data, buf, offset + 2);
      buf.writeUInt16BE(name.encode.bytes, offset);
      rptr.encode.bytes = name.encode.bytes + 2;
      return buf;
    };
    rptr.encode.bytes = 0;
    rptr.decode = function(buf, offset) {
      if (!offset) offset = 0;
      const data = name.decode(buf, offset + 2);
      rptr.decode.bytes = name.decode.bytes + 2;
      return data;
    };
    rptr.decode.bytes = 0;
    rptr.encodingLength = function(data) {
      return name.encodingLength(data) + 2;
    };
    const rsrv = exports$1.srv = {};
    rsrv.encode = function(data, buf, offset) {
      if (!buf) buf = Buffer2.alloc(rsrv.encodingLength(data));
      if (!offset) offset = 0;
      buf.writeUInt16BE(data.priority || 0, offset + 2);
      buf.writeUInt16BE(data.weight || 0, offset + 4);
      buf.writeUInt16BE(data.port || 0, offset + 6);
      name.encode(data.target, buf, offset + 8);
      const len = name.encode.bytes + 6;
      buf.writeUInt16BE(len, offset);
      rsrv.encode.bytes = len + 2;
      return buf;
    };
    rsrv.encode.bytes = 0;
    rsrv.decode = function(buf, offset) {
      if (!offset) offset = 0;
      const len = buf.readUInt16BE(offset);
      const data = {};
      data.priority = buf.readUInt16BE(offset + 2);
      data.weight = buf.readUInt16BE(offset + 4);
      data.port = buf.readUInt16BE(offset + 6);
      data.target = name.decode(buf, offset + 8);
      rsrv.decode.bytes = len + 2;
      return data;
    };
    rsrv.decode.bytes = 0;
    rsrv.encodingLength = function(data) {
      return 8 + name.encodingLength(data.target);
    };
    const rcaa = exports$1.caa = {};
    rcaa.ISSUER_CRITICAL = 1 << 7;
    rcaa.encode = function(data, buf, offset) {
      const len = rcaa.encodingLength(data);
      if (!buf) buf = Buffer2.alloc(rcaa.encodingLength(data));
      if (!offset) offset = 0;
      if (data.issuerCritical) {
        data.flags = rcaa.ISSUER_CRITICAL;
      }
      buf.writeUInt16BE(len - 2, offset);
      offset += 2;
      buf.writeUInt8(data.flags || 0, offset);
      offset += 1;
      string.encode(data.tag, buf, offset);
      offset += string.encode.bytes;
      buf.write(data.value, offset);
      offset += Buffer2.byteLength(data.value);
      rcaa.encode.bytes = len;
      return buf;
    };
    rcaa.encode.bytes = 0;
    rcaa.decode = function(buf, offset) {
      if (!offset) offset = 0;
      const len = buf.readUInt16BE(offset);
      offset += 2;
      const oldOffset = offset;
      const data = {};
      data.flags = buf.readUInt8(offset);
      offset += 1;
      data.tag = string.decode(buf, offset);
      offset += string.decode.bytes;
      data.value = buf.toString("utf-8", offset, oldOffset + len);
      data.issuerCritical = !!(data.flags & rcaa.ISSUER_CRITICAL);
      rcaa.decode.bytes = len + 2;
      return data;
    };
    rcaa.decode.bytes = 0;
    rcaa.encodingLength = function(data) {
      return string.encodingLength(data.tag) + string.encodingLength(data.value) + 2;
    };
    const rmx = exports$1.mx = {};
    rmx.encode = function(data, buf, offset) {
      if (!buf) buf = Buffer2.alloc(rmx.encodingLength(data));
      if (!offset) offset = 0;
      const oldOffset = offset;
      offset += 2;
      buf.writeUInt16BE(data.preference || 0, offset);
      offset += 2;
      name.encode(data.exchange, buf, offset);
      offset += name.encode.bytes;
      buf.writeUInt16BE(offset - oldOffset - 2, oldOffset);
      rmx.encode.bytes = offset - oldOffset;
      return buf;
    };
    rmx.encode.bytes = 0;
    rmx.decode = function(buf, offset) {
      if (!offset) offset = 0;
      const oldOffset = offset;
      const data = {};
      offset += 2;
      data.preference = buf.readUInt16BE(offset);
      offset += 2;
      data.exchange = name.decode(buf, offset);
      offset += name.decode.bytes;
      rmx.decode.bytes = offset - oldOffset;
      return data;
    };
    rmx.encodingLength = function(data) {
      return 4 + name.encodingLength(data.exchange);
    };
    const ra = exports$1.a = {};
    ra.encode = function(host, buf, offset) {
      if (!buf) buf = Buffer2.alloc(ra.encodingLength(host));
      if (!offset) offset = 0;
      buf.writeUInt16BE(4, offset);
      offset += 2;
      ip.v4.encode(host, buf, offset);
      ra.encode.bytes = 6;
      return buf;
    };
    ra.encode.bytes = 0;
    ra.decode = function(buf, offset) {
      if (!offset) offset = 0;
      offset += 2;
      const host = ip.v4.decode(buf, offset);
      ra.decode.bytes = 6;
      return host;
    };
    ra.decode.bytes = 0;
    ra.encodingLength = function() {
      return 6;
    };
    const raaaa = exports$1.aaaa = {};
    raaaa.encode = function(host, buf, offset) {
      if (!buf) buf = Buffer2.alloc(raaaa.encodingLength(host));
      if (!offset) offset = 0;
      buf.writeUInt16BE(16, offset);
      offset += 2;
      ip.v6.encode(host, buf, offset);
      raaaa.encode.bytes = 18;
      return buf;
    };
    raaaa.encode.bytes = 0;
    raaaa.decode = function(buf, offset) {
      if (!offset) offset = 0;
      offset += 2;
      const host = ip.v6.decode(buf, offset);
      raaaa.decode.bytes = 18;
      return host;
    };
    raaaa.decode.bytes = 0;
    raaaa.encodingLength = function() {
      return 18;
    };
    const roption = exports$1.option = {};
    roption.encode = function(option, buf, offset) {
      if (!buf) buf = Buffer2.alloc(roption.encodingLength(option));
      if (!offset) offset = 0;
      const oldOffset = offset;
      const code = optioncodes2.toCode(option.code);
      buf.writeUInt16BE(code, offset);
      offset += 2;
      if (option.data) {
        buf.writeUInt16BE(option.data.length, offset);
        offset += 2;
        option.data.copy(buf, offset);
        offset += option.data.length;
      } else {
        switch (code) {
          // case 3: NSID.  No encode makes sense.
          // case 5,6,7: Not implementable
          case 8:
            const spl = option.sourcePrefixLength || 0;
            const fam = option.family || ip.familyOf(option.ip);
            const ipBuf = ip.encode(option.ip, Buffer2.alloc);
            const ipLen = Math.ceil(spl / 8);
            buf.writeUInt16BE(ipLen + 4, offset);
            offset += 2;
            buf.writeUInt16BE(fam, offset);
            offset += 2;
            buf.writeUInt8(spl, offset++);
            buf.writeUInt8(option.scopePrefixLength || 0, offset++);
            ipBuf.copy(buf, offset, 0, ipLen);
            offset += ipLen;
            break;
          // case 9: EXPIRE (experimental)
          // case 10: COOKIE.  No encode makes sense.
          case 11:
            if (option.timeout) {
              buf.writeUInt16BE(2, offset);
              offset += 2;
              buf.writeUInt16BE(option.timeout, offset);
              offset += 2;
            } else {
              buf.writeUInt16BE(0, offset);
              offset += 2;
            }
            break;
          case 12:
            const len = option.length || 0;
            buf.writeUInt16BE(len, offset);
            offset += 2;
            buf.fill(0, offset, offset + len);
            offset += len;
            break;
          // case 13:  CHAIN.  Experimental.
          case 14:
            const tagsLen = option.tags.length * 2;
            buf.writeUInt16BE(tagsLen, offset);
            offset += 2;
            for (const tag of option.tags) {
              buf.writeUInt16BE(tag, offset);
              offset += 2;
            }
            break;
          default:
            throw new Error(`Unknown roption code: ${option.code}`);
        }
      }
      roption.encode.bytes = offset - oldOffset;
      return buf;
    };
    roption.encode.bytes = 0;
    roption.decode = function(buf, offset) {
      if (!offset) offset = 0;
      const option = {};
      option.code = buf.readUInt16BE(offset);
      option.type = optioncodes2.toString(option.code);
      offset += 2;
      const len = buf.readUInt16BE(offset);
      offset += 2;
      option.data = buf.slice(offset, offset + len);
      switch (option.code) {
        // case 3: NSID.  No decode makes sense.
        case 8:
          option.family = buf.readUInt16BE(offset);
          offset += 2;
          option.sourcePrefixLength = buf.readUInt8(offset++);
          option.scopePrefixLength = buf.readUInt8(offset++);
          const padded = Buffer2.alloc(option.family === 1 ? 4 : 16);
          buf.copy(padded, 0, offset, offset + len - 4);
          option.ip = ip.decode(padded);
          break;
        // case 12: Padding.  No decode makes sense.
        case 11:
          if (len > 0) {
            option.timeout = buf.readUInt16BE(offset);
            offset += 2;
          }
          break;
        case 14:
          option.tags = [];
          for (let i = 0; i < len; i += 2) {
            option.tags.push(buf.readUInt16BE(offset));
            offset += 2;
          }
      }
      roption.decode.bytes = len + 4;
      return option;
    };
    roption.decode.bytes = 0;
    roption.encodingLength = function(option) {
      if (option.data) {
        return option.data.length + 4;
      }
      const code = optioncodes2.toCode(option.code);
      switch (code) {
        case 8:
          const spl = option.sourcePrefixLength || 0;
          return Math.ceil(spl / 8) + 8;
        case 11:
          return typeof option.timeout === "number" ? 6 : 4;
        case 12:
          return option.length + 4;
        case 14:
          return 4 + option.tags.length * 2;
      }
      throw new Error(`Unknown roption code: ${option.code}`);
    };
    const ropt = exports$1.opt = {};
    ropt.encode = function(options, buf, offset) {
      if (!buf) buf = Buffer2.alloc(ropt.encodingLength(options));
      if (!offset) offset = 0;
      const oldOffset = offset;
      const rdlen = encodingLengthList(options, roption);
      buf.writeUInt16BE(rdlen, offset);
      offset = encodeList(options, roption, buf, offset + 2);
      ropt.encode.bytes = offset - oldOffset;
      return buf;
    };
    ropt.encode.bytes = 0;
    ropt.decode = function(buf, offset) {
      if (!offset) offset = 0;
      const oldOffset = offset;
      const options = [];
      let rdlen = buf.readUInt16BE(offset);
      offset += 2;
      let o = 0;
      while (rdlen > 0) {
        options[o++] = roption.decode(buf, offset);
        offset += roption.decode.bytes;
        rdlen -= roption.decode.bytes;
      }
      ropt.decode.bytes = offset - oldOffset;
      return options;
    };
    ropt.decode.bytes = 0;
    ropt.encodingLength = function(options) {
      return 2 + encodingLengthList(options || [], roption);
    };
    const rdnskey = exports$1.dnskey = {};
    rdnskey.PROTOCOL_DNSSEC = 3;
    rdnskey.ZONE_KEY = 128;
    rdnskey.SECURE_ENTRYPOINT = 32768;
    rdnskey.encode = function(key, buf, offset) {
      if (!buf) buf = Buffer2.alloc(rdnskey.encodingLength(key));
      if (!offset) offset = 0;
      const oldOffset = offset;
      const keydata = key.key;
      if (!Buffer2.isBuffer(keydata)) {
        throw new Error("Key must be a Buffer");
      }
      offset += 2;
      buf.writeUInt16BE(key.flags, offset);
      offset += 2;
      buf.writeUInt8(rdnskey.PROTOCOL_DNSSEC, offset);
      offset += 1;
      buf.writeUInt8(key.algorithm, offset);
      offset += 1;
      keydata.copy(buf, offset, 0, keydata.length);
      offset += keydata.length;
      rdnskey.encode.bytes = offset - oldOffset;
      buf.writeUInt16BE(rdnskey.encode.bytes - 2, oldOffset);
      return buf;
    };
    rdnskey.encode.bytes = 0;
    rdnskey.decode = function(buf, offset) {
      if (!offset) offset = 0;
      const oldOffset = offset;
      var key = {};
      var length = buf.readUInt16BE(offset);
      offset += 2;
      key.flags = buf.readUInt16BE(offset);
      offset += 2;
      if (buf.readUInt8(offset) !== rdnskey.PROTOCOL_DNSSEC) {
        throw new Error("Protocol must be 3");
      }
      offset += 1;
      key.algorithm = buf.readUInt8(offset);
      offset += 1;
      key.key = buf.slice(offset, oldOffset + length + 2);
      offset += key.key.length;
      rdnskey.decode.bytes = offset - oldOffset;
      return key;
    };
    rdnskey.decode.bytes = 0;
    rdnskey.encodingLength = function(key) {
      return 6 + Buffer2.byteLength(key.key);
    };
    const rrrsig = exports$1.rrsig = {};
    rrrsig.encode = function(sig, buf, offset) {
      if (!buf) buf = Buffer2.alloc(rrrsig.encodingLength(sig));
      if (!offset) offset = 0;
      const oldOffset = offset;
      const signature = sig.signature;
      if (!Buffer2.isBuffer(signature)) {
        throw new Error("Signature must be a Buffer");
      }
      offset += 2;
      buf.writeUInt16BE(types2.toType(sig.typeCovered), offset);
      offset += 2;
      buf.writeUInt8(sig.algorithm, offset);
      offset += 1;
      buf.writeUInt8(sig.labels, offset);
      offset += 1;
      buf.writeUInt32BE(sig.originalTTL, offset);
      offset += 4;
      buf.writeUInt32BE(sig.expiration, offset);
      offset += 4;
      buf.writeUInt32BE(sig.inception, offset);
      offset += 4;
      buf.writeUInt16BE(sig.keyTag, offset);
      offset += 2;
      name.encode(sig.signersName, buf, offset);
      offset += name.encode.bytes;
      signature.copy(buf, offset, 0, signature.length);
      offset += signature.length;
      rrrsig.encode.bytes = offset - oldOffset;
      buf.writeUInt16BE(rrrsig.encode.bytes - 2, oldOffset);
      return buf;
    };
    rrrsig.encode.bytes = 0;
    rrrsig.decode = function(buf, offset) {
      if (!offset) offset = 0;
      const oldOffset = offset;
      var sig = {};
      var length = buf.readUInt16BE(offset);
      offset += 2;
      sig.typeCovered = types2.toString(buf.readUInt16BE(offset));
      offset += 2;
      sig.algorithm = buf.readUInt8(offset);
      offset += 1;
      sig.labels = buf.readUInt8(offset);
      offset += 1;
      sig.originalTTL = buf.readUInt32BE(offset);
      offset += 4;
      sig.expiration = buf.readUInt32BE(offset);
      offset += 4;
      sig.inception = buf.readUInt32BE(offset);
      offset += 4;
      sig.keyTag = buf.readUInt16BE(offset);
      offset += 2;
      sig.signersName = name.decode(buf, offset);
      offset += name.decode.bytes;
      sig.signature = buf.slice(offset, oldOffset + length + 2);
      offset += sig.signature.length;
      rrrsig.decode.bytes = offset - oldOffset;
      return sig;
    };
    rrrsig.decode.bytes = 0;
    rrrsig.encodingLength = function(sig) {
      return 20 + name.encodingLength(sig.signersName) + Buffer2.byteLength(sig.signature);
    };
    const rrp = exports$1.rp = {};
    rrp.encode = function(data, buf, offset) {
      if (!buf) buf = Buffer2.alloc(rrp.encodingLength(data));
      if (!offset) offset = 0;
      const oldOffset = offset;
      offset += 2;
      name.encode(data.mbox || ".", buf, offset, { mail: true });
      offset += name.encode.bytes;
      name.encode(data.txt || ".", buf, offset);
      offset += name.encode.bytes;
      rrp.encode.bytes = offset - oldOffset;
      buf.writeUInt16BE(rrp.encode.bytes - 2, oldOffset);
      return buf;
    };
    rrp.encode.bytes = 0;
    rrp.decode = function(buf, offset) {
      if (!offset) offset = 0;
      const oldOffset = offset;
      const data = {};
      offset += 2;
      data.mbox = name.decode(buf, offset, { mail: true }) || ".";
      offset += name.decode.bytes;
      data.txt = name.decode(buf, offset) || ".";
      offset += name.decode.bytes;
      rrp.decode.bytes = offset - oldOffset;
      return data;
    };
    rrp.decode.bytes = 0;
    rrp.encodingLength = function(data) {
      return 2 + name.encodingLength(data.mbox || ".") + name.encodingLength(data.txt || ".");
    };
    const typebitmap = {};
    typebitmap.encode = function(typelist, buf, offset) {
      if (!buf) buf = Buffer2.alloc(typebitmap.encodingLength(typelist));
      if (!offset) offset = 0;
      const oldOffset = offset;
      var typesByWindow = [];
      for (var i = 0; i < typelist.length; i++) {
        var typeid = types2.toType(typelist[i]);
        if (typesByWindow[typeid >> 8] === void 0) {
          typesByWindow[typeid >> 8] = [];
        }
        typesByWindow[typeid >> 8][typeid >> 3 & 31] |= 1 << 7 - (typeid & 7);
      }
      for (i = 0; i < typesByWindow.length; i++) {
        if (typesByWindow[i] !== void 0) {
          var windowBuf = Buffer2.from(typesByWindow[i]);
          buf.writeUInt8(i, offset);
          offset += 1;
          buf.writeUInt8(windowBuf.length, offset);
          offset += 1;
          windowBuf.copy(buf, offset);
          offset += windowBuf.length;
        }
      }
      typebitmap.encode.bytes = offset - oldOffset;
      return buf;
    };
    typebitmap.encode.bytes = 0;
    typebitmap.decode = function(buf, offset, length) {
      if (!offset) offset = 0;
      const oldOffset = offset;
      var typelist = [];
      while (offset - oldOffset < length) {
        var window = buf.readUInt8(offset);
        offset += 1;
        var windowLength = buf.readUInt8(offset);
        offset += 1;
        for (var i = 0; i < windowLength; i++) {
          var b = buf.readUInt8(offset + i);
          for (var j = 0; j < 8; j++) {
            if (b & 1 << 7 - j) {
              var typeid = types2.toString(window << 8 | i << 3 | j);
              typelist.push(typeid);
            }
          }
        }
        offset += windowLength;
      }
      typebitmap.decode.bytes = offset - oldOffset;
      return typelist;
    };
    typebitmap.decode.bytes = 0;
    typebitmap.encodingLength = function(typelist) {
      var extents = [];
      for (var i = 0; i < typelist.length; i++) {
        var typeid = types2.toType(typelist[i]);
        extents[typeid >> 8] = Math.max(extents[typeid >> 8] || 0, typeid & 255);
      }
      var len = 0;
      for (i = 0; i < extents.length; i++) {
        if (extents[i] !== void 0) {
          len += 2 + Math.ceil((extents[i] + 1) / 8);
        }
      }
      return len;
    };
    const rnsec = exports$1.nsec = {};
    rnsec.encode = function(record, buf, offset) {
      if (!buf) buf = Buffer2.alloc(rnsec.encodingLength(record));
      if (!offset) offset = 0;
      const oldOffset = offset;
      offset += 2;
      name.encode(record.nextDomain, buf, offset);
      offset += name.encode.bytes;
      typebitmap.encode(record.rrtypes, buf, offset);
      offset += typebitmap.encode.bytes;
      rnsec.encode.bytes = offset - oldOffset;
      buf.writeUInt16BE(rnsec.encode.bytes - 2, oldOffset);
      return buf;
    };
    rnsec.encode.bytes = 0;
    rnsec.decode = function(buf, offset) {
      if (!offset) offset = 0;
      const oldOffset = offset;
      var record = {};
      var length = buf.readUInt16BE(offset);
      offset += 2;
      record.nextDomain = name.decode(buf, offset);
      offset += name.decode.bytes;
      record.rrtypes = typebitmap.decode(buf, offset, length - (offset - oldOffset));
      offset += typebitmap.decode.bytes;
      rnsec.decode.bytes = offset - oldOffset;
      return record;
    };
    rnsec.decode.bytes = 0;
    rnsec.encodingLength = function(record) {
      return 2 + name.encodingLength(record.nextDomain) + typebitmap.encodingLength(record.rrtypes);
    };
    const rnsec3 = exports$1.nsec3 = {};
    rnsec3.encode = function(record, buf, offset) {
      if (!buf) buf = Buffer2.alloc(rnsec3.encodingLength(record));
      if (!offset) offset = 0;
      const oldOffset = offset;
      const salt = record.salt;
      if (!Buffer2.isBuffer(salt)) {
        throw new Error("salt must be a Buffer");
      }
      const nextDomain = record.nextDomain;
      if (!Buffer2.isBuffer(nextDomain)) {
        throw new Error("nextDomain must be a Buffer");
      }
      offset += 2;
      buf.writeUInt8(record.algorithm, offset);
      offset += 1;
      buf.writeUInt8(record.flags, offset);
      offset += 1;
      buf.writeUInt16BE(record.iterations, offset);
      offset += 2;
      buf.writeUInt8(salt.length, offset);
      offset += 1;
      salt.copy(buf, offset, 0, salt.length);
      offset += salt.length;
      buf.writeUInt8(nextDomain.length, offset);
      offset += 1;
      nextDomain.copy(buf, offset, 0, nextDomain.length);
      offset += nextDomain.length;
      typebitmap.encode(record.rrtypes, buf, offset);
      offset += typebitmap.encode.bytes;
      rnsec3.encode.bytes = offset - oldOffset;
      buf.writeUInt16BE(rnsec3.encode.bytes - 2, oldOffset);
      return buf;
    };
    rnsec3.encode.bytes = 0;
    rnsec3.decode = function(buf, offset) {
      if (!offset) offset = 0;
      const oldOffset = offset;
      var record = {};
      var length = buf.readUInt16BE(offset);
      offset += 2;
      record.algorithm = buf.readUInt8(offset);
      offset += 1;
      record.flags = buf.readUInt8(offset);
      offset += 1;
      record.iterations = buf.readUInt16BE(offset);
      offset += 2;
      const saltLength = buf.readUInt8(offset);
      offset += 1;
      record.salt = buf.slice(offset, offset + saltLength);
      offset += saltLength;
      const hashLength = buf.readUInt8(offset);
      offset += 1;
      record.nextDomain = buf.slice(offset, offset + hashLength);
      offset += hashLength;
      record.rrtypes = typebitmap.decode(buf, offset, length - (offset - oldOffset));
      offset += typebitmap.decode.bytes;
      rnsec3.decode.bytes = offset - oldOffset;
      return record;
    };
    rnsec3.decode.bytes = 0;
    rnsec3.encodingLength = function(record) {
      return 8 + record.salt.length + record.nextDomain.length + typebitmap.encodingLength(record.rrtypes);
    };
    const rds = exports$1.ds = {};
    rds.encode = function(digest, buf, offset) {
      if (!buf) buf = Buffer2.alloc(rds.encodingLength(digest));
      if (!offset) offset = 0;
      const oldOffset = offset;
      const digestdata = digest.digest;
      if (!Buffer2.isBuffer(digestdata)) {
        throw new Error("Digest must be a Buffer");
      }
      offset += 2;
      buf.writeUInt16BE(digest.keyTag, offset);
      offset += 2;
      buf.writeUInt8(digest.algorithm, offset);
      offset += 1;
      buf.writeUInt8(digest.digestType, offset);
      offset += 1;
      digestdata.copy(buf, offset, 0, digestdata.length);
      offset += digestdata.length;
      rds.encode.bytes = offset - oldOffset;
      buf.writeUInt16BE(rds.encode.bytes - 2, oldOffset);
      return buf;
    };
    rds.encode.bytes = 0;
    rds.decode = function(buf, offset) {
      if (!offset) offset = 0;
      const oldOffset = offset;
      var digest = {};
      var length = buf.readUInt16BE(offset);
      offset += 2;
      digest.keyTag = buf.readUInt16BE(offset);
      offset += 2;
      digest.algorithm = buf.readUInt8(offset);
      offset += 1;
      digest.digestType = buf.readUInt8(offset);
      offset += 1;
      digest.digest = buf.slice(offset, oldOffset + length + 2);
      offset += digest.digest.length;
      rds.decode.bytes = offset - oldOffset;
      return digest;
    };
    rds.decode.bytes = 0;
    rds.encodingLength = function(digest) {
      return 6 + Buffer2.byteLength(digest.digest);
    };
    const rsshfp = exports$1.sshfp = {};
    rsshfp.getFingerprintLengthForHashType = function getFingerprintLengthForHashType(hashType) {
      switch (hashType) {
        case 1:
          return 20;
        case 2:
          return 32;
      }
    };
    rsshfp.encode = function encode(record, buf, offset) {
      if (!buf) buf = Buffer2.alloc(rsshfp.encodingLength(record));
      if (!offset) offset = 0;
      const oldOffset = offset;
      offset += 2;
      buf[offset] = record.algorithm;
      offset += 1;
      buf[offset] = record.hash;
      offset += 1;
      const fingerprintBuf = Buffer2.from(record.fingerprint.toUpperCase(), "hex");
      if (fingerprintBuf.length !== rsshfp.getFingerprintLengthForHashType(record.hash)) {
        throw new Error("Invalid fingerprint length");
      }
      fingerprintBuf.copy(buf, offset);
      offset += fingerprintBuf.byteLength;
      rsshfp.encode.bytes = offset - oldOffset;
      buf.writeUInt16BE(rsshfp.encode.bytes - 2, oldOffset);
      return buf;
    };
    rsshfp.encode.bytes = 0;
    rsshfp.decode = function decode(buf, offset) {
      if (!offset) offset = 0;
      const oldOffset = offset;
      const record = {};
      offset += 2;
      record.algorithm = buf[offset];
      offset += 1;
      record.hash = buf[offset];
      offset += 1;
      const fingerprintLength = rsshfp.getFingerprintLengthForHashType(record.hash);
      record.fingerprint = buf.slice(offset, offset + fingerprintLength).toString("hex").toUpperCase();
      offset += fingerprintLength;
      rsshfp.decode.bytes = offset - oldOffset;
      return record;
    };
    rsshfp.decode.bytes = 0;
    rsshfp.encodingLength = function(record) {
      return 4 + Buffer2.from(record.fingerprint, "hex").byteLength;
    };
    const rnaptr = exports$1.naptr = {};
    rnaptr.encode = function(data, buf, offset) {
      if (!buf) buf = Buffer2.alloc(rnaptr.encodingLength(data));
      if (!offset) offset = 0;
      const oldOffset = offset;
      offset += 2;
      buf.writeUInt16BE(data.order || 0, offset);
      offset += 2;
      buf.writeUInt16BE(data.preference || 0, offset);
      offset += 2;
      string.encode(data.flags, buf, offset);
      offset += string.encode.bytes;
      string.encode(data.services, buf, offset);
      offset += string.encode.bytes;
      string.encode(data.regexp, buf, offset);
      offset += string.encode.bytes;
      name.encode(data.replacement, buf, offset);
      offset += name.encode.bytes;
      rnaptr.encode.bytes = offset - oldOffset;
      buf.writeUInt16BE(rnaptr.encode.bytes - 2, oldOffset);
      return buf;
    };
    rnaptr.encode.bytes = 0;
    rnaptr.decode = function(buf, offset) {
      if (!offset) offset = 0;
      const oldOffset = offset;
      const data = {};
      offset += 2;
      data.order = buf.readUInt16BE(offset);
      offset += 2;
      data.preference = buf.readUInt16BE(offset);
      offset += 2;
      data.flags = string.decode(buf, offset);
      offset += string.decode.bytes;
      data.services = string.decode(buf, offset);
      offset += string.decode.bytes;
      data.regexp = string.decode(buf, offset);
      offset += string.decode.bytes;
      data.replacement = name.decode(buf, offset);
      offset += name.decode.bytes;
      rnaptr.decode.bytes = offset - oldOffset;
      return data;
    };
    rnaptr.decode.bytes = 0;
    rnaptr.encodingLength = function(data) {
      return string.encodingLength(data.flags) + string.encodingLength(data.services) + string.encodingLength(data.regexp) + name.encodingLength(data.replacement) + 6;
    };
    const rtlsa = exports$1.tlsa = {};
    rtlsa.encode = function(cert, buf, offset) {
      if (!buf) buf = Buffer2.alloc(rtlsa.encodingLength(cert));
      if (!offset) offset = 0;
      const oldOffset = offset;
      const certdata = cert.certificate;
      if (!Buffer2.isBuffer(certdata)) {
        throw new Error("Certificate must be a Buffer");
      }
      offset += 2;
      buf.writeUInt8(cert.usage, offset);
      offset += 1;
      buf.writeUInt8(cert.selector, offset);
      offset += 1;
      buf.writeUInt8(cert.matchingType, offset);
      offset += 1;
      certdata.copy(buf, offset, 0, certdata.length);
      offset += certdata.length;
      rtlsa.encode.bytes = offset - oldOffset;
      buf.writeUInt16BE(rtlsa.encode.bytes - 2, oldOffset);
      return buf;
    };
    rtlsa.encode.bytes = 0;
    rtlsa.decode = function(buf, offset) {
      if (!offset) offset = 0;
      const oldOffset = offset;
      const cert = {};
      const length = buf.readUInt16BE(offset);
      offset += 2;
      cert.usage = buf.readUInt8(offset);
      offset += 1;
      cert.selector = buf.readUInt8(offset);
      offset += 1;
      cert.matchingType = buf.readUInt8(offset);
      offset += 1;
      cert.certificate = buf.slice(offset, oldOffset + length + 2);
      offset += cert.certificate.length;
      rtlsa.decode.bytes = offset - oldOffset;
      return cert;
    };
    rtlsa.decode.bytes = 0;
    rtlsa.encodingLength = function(cert) {
      return 5 + Buffer2.byteLength(cert.certificate);
    };
    const renc = exports$1.record = function(type) {
      switch (type.toUpperCase()) {
        case "A":
          return ra;
        case "PTR":
          return rptr;
        case "CNAME":
          return rcname;
        case "DNAME":
          return rdname;
        case "TXT":
          return rtxt;
        case "NULL":
          return rnull;
        case "AAAA":
          return raaaa;
        case "SRV":
          return rsrv;
        case "HINFO":
          return rhinfo;
        case "CAA":
          return rcaa;
        case "NS":
          return rns;
        case "SOA":
          return rsoa;
        case "MX":
          return rmx;
        case "OPT":
          return ropt;
        case "DNSKEY":
          return rdnskey;
        case "RRSIG":
          return rrrsig;
        case "RP":
          return rrp;
        case "NSEC":
          return rnsec;
        case "NSEC3":
          return rnsec3;
        case "SSHFP":
          return rsshfp;
        case "DS":
          return rds;
        case "NAPTR":
          return rnaptr;
        case "TLSA":
          return rtlsa;
      }
      return runknown;
    };
    const answer = exports$1.answer = {};
    answer.encode = function(a, buf, offset) {
      if (!buf) buf = Buffer2.alloc(answer.encodingLength(a));
      if (!offset) offset = 0;
      const oldOffset = offset;
      name.encode(a.name, buf, offset);
      offset += name.encode.bytes;
      buf.writeUInt16BE(types2.toType(a.type), offset);
      if (a.type.toUpperCase() === "OPT") {
        if (a.name !== ".") {
          throw new Error("OPT name must be root.");
        }
        buf.writeUInt16BE(a.udpPayloadSize || 4096, offset + 2);
        buf.writeUInt8(a.extendedRcode || 0, offset + 4);
        buf.writeUInt8(a.ednsVersion || 0, offset + 5);
        buf.writeUInt16BE(a.flags || 0, offset + 6);
        offset += 8;
        ropt.encode(a.options || [], buf, offset);
        offset += ropt.encode.bytes;
      } else {
        let klass = classes2.toClass(a.class === void 0 ? "IN" : a.class);
        if (a.flush) klass |= FLUSH_MASK;
        buf.writeUInt16BE(klass, offset + 2);
        buf.writeUInt32BE(a.ttl || 0, offset + 4);
        offset += 8;
        const enc = renc(a.type);
        enc.encode(a.data, buf, offset);
        offset += enc.encode.bytes;
      }
      answer.encode.bytes = offset - oldOffset;
      return buf;
    };
    answer.encode.bytes = 0;
    answer.decode = function(buf, offset) {
      if (!offset) offset = 0;
      const a = {};
      const oldOffset = offset;
      a.name = name.decode(buf, offset);
      offset += name.decode.bytes;
      a.type = types2.toString(buf.readUInt16BE(offset));
      if (a.type === "OPT") {
        a.udpPayloadSize = buf.readUInt16BE(offset + 2);
        a.extendedRcode = buf.readUInt8(offset + 4);
        a.ednsVersion = buf.readUInt8(offset + 5);
        a.flags = buf.readUInt16BE(offset + 6);
        a.flag_do = (a.flags >> 15 & 1) === 1;
        a.options = ropt.decode(buf, offset + 8);
        offset += 8 + ropt.decode.bytes;
      } else {
        const klass = buf.readUInt16BE(offset + 2);
        a.ttl = buf.readUInt32BE(offset + 4);
        a.class = classes2.toString(klass & NOT_FLUSH_MASK);
        a.flush = !!(klass & FLUSH_MASK);
        const enc = renc(a.type);
        a.data = enc.decode(buf, offset + 8);
        offset += 8 + enc.decode.bytes;
      }
      answer.decode.bytes = offset - oldOffset;
      return a;
    };
    answer.decode.bytes = 0;
    answer.encodingLength = function(a) {
      const data = a.data !== null && a.data !== void 0 ? a.data : a.options;
      return name.encodingLength(a.name) + 8 + renc(a.type).encodingLength(data);
    };
    const question = exports$1.question = {};
    question.encode = function(q, buf, offset) {
      if (!buf) buf = Buffer2.alloc(question.encodingLength(q));
      if (!offset) offset = 0;
      const oldOffset = offset;
      name.encode(q.name, buf, offset);
      offset += name.encode.bytes;
      buf.writeUInt16BE(types2.toType(q.type), offset);
      offset += 2;
      buf.writeUInt16BE(classes2.toClass(q.class === void 0 ? "IN" : q.class), offset);
      offset += 2;
      question.encode.bytes = offset - oldOffset;
      return q;
    };
    question.encode.bytes = 0;
    question.decode = function(buf, offset) {
      if (!offset) offset = 0;
      const oldOffset = offset;
      const q = {};
      q.name = name.decode(buf, offset);
      offset += name.decode.bytes;
      q.type = types2.toString(buf.readUInt16BE(offset));
      offset += 2;
      q.class = classes2.toString(buf.readUInt16BE(offset));
      offset += 2;
      const qu = !!(q.class & QU_MASK);
      if (qu) q.class &= NOT_QU_MASK;
      question.decode.bytes = offset - oldOffset;
      return q;
    };
    question.decode.bytes = 0;
    question.encodingLength = function(q) {
      return name.encodingLength(q.name) + 4;
    };
    exports$1.AUTHORITATIVE_ANSWER = 1 << 10;
    exports$1.TRUNCATED_RESPONSE = 1 << 9;
    exports$1.RECURSION_DESIRED = 1 << 8;
    exports$1.RECURSION_AVAILABLE = 1 << 7;
    exports$1.AUTHENTIC_DATA = 1 << 5;
    exports$1.CHECKING_DISABLED = 1 << 4;
    exports$1.DNSSEC_OK = 1 << 15;
    exports$1.encode = function(result, buf, offset) {
      const allocing = !buf;
      if (allocing) buf = Buffer2.alloc(exports$1.encodingLength(result));
      if (!offset) offset = 0;
      const oldOffset = offset;
      if (!result.questions) result.questions = [];
      if (!result.answers) result.answers = [];
      if (!result.authorities) result.authorities = [];
      if (!result.additionals) result.additionals = [];
      header.encode(result, buf, offset);
      offset += header.encode.bytes;
      offset = encodeList(result.questions, question, buf, offset);
      offset = encodeList(result.answers, answer, buf, offset);
      offset = encodeList(result.authorities, answer, buf, offset);
      offset = encodeList(result.additionals, answer, buf, offset);
      exports$1.encode.bytes = offset - oldOffset;
      if (allocing && exports$1.encode.bytes !== buf.length) {
        return buf.slice(0, exports$1.encode.bytes);
      }
      return buf;
    };
    exports$1.encode.bytes = 0;
    exports$1.decode = function(buf, offset) {
      if (!offset) offset = 0;
      const oldOffset = offset;
      const result = header.decode(buf, offset);
      offset += header.decode.bytes;
      offset = decodeList(result.questions, question, buf, offset);
      offset = decodeList(result.answers, answer, buf, offset);
      offset = decodeList(result.authorities, answer, buf, offset);
      offset = decodeList(result.additionals, answer, buf, offset);
      exports$1.decode.bytes = offset - oldOffset;
      return result;
    };
    exports$1.decode.bytes = 0;
    exports$1.encodingLength = function(result) {
      return header.encodingLength(result) + encodingLengthList(result.questions || [], question) + encodingLengthList(result.answers || [], answer) + encodingLengthList(result.authorities || [], answer) + encodingLengthList(result.additionals || [], answer);
    };
    exports$1.streamEncode = function(result) {
      const buf = exports$1.encode(result);
      const sbuf = Buffer2.alloc(2);
      sbuf.writeUInt16BE(buf.byteLength);
      const combine = Buffer2.concat([sbuf, buf]);
      exports$1.streamEncode.bytes = combine.byteLength;
      return combine;
    };
    exports$1.streamEncode.bytes = 0;
    exports$1.streamDecode = function(sbuf) {
      const len = sbuf.readUInt16BE(0);
      if (sbuf.byteLength < len + 2) {
        return null;
      }
      const result = exports$1.decode(sbuf.slice(2));
      exports$1.streamDecode.bytes = exports$1.decode.bytes;
      return result;
    };
    exports$1.streamDecode.bytes = 0;
    function encodingLengthList(list, enc) {
      let len = 0;
      for (let i = 0; i < list.length; i++) len += enc.encodingLength(list[i]);
      return len;
    }
    function encodeList(list, enc, buf, offset) {
      for (let i = 0; i < list.length; i++) {
        enc.encode(list[i], buf, offset);
        offset += enc.encode.bytes;
      }
      return offset;
    }
    function decodeList(list, enc, buf, offset) {
      for (let i = 0; i < list.length; i++) {
        list[i] = enc.decode(buf, offset);
        offset += enc.decode.bytes;
      }
      return offset;
    }
  })(dnsPacket);
  return dnsPacket;
}
var thunky_1;
var hasRequiredThunky;
function requireThunky() {
  if (hasRequiredThunky) return thunky_1;
  hasRequiredThunky = 1;
  var nextTick = nextTickArgs;
  process.nextTick(upgrade, 42);
  thunky_1 = thunky;
  function thunky(fn) {
    var state = run;
    return thunk;
    function thunk(callback) {
      state(callback || noop);
    }
    function run(callback) {
      var stack = [callback];
      state = wait;
      fn(done);
      function wait(callback2) {
        stack.push(callback2);
      }
      function done(err) {
        var args = arguments;
        state = isError(err) ? run : finished;
        while (stack.length) finished(stack.shift());
        function finished(callback2) {
          nextTick(apply, callback2, args);
        }
      }
    }
  }
  function isError(err) {
    return Object.prototype.toString.call(err) === "[object Error]";
  }
  function noop() {
  }
  function apply(callback, args) {
    callback.apply(null, args);
  }
  function upgrade(val) {
    if (val === 42) nextTick = process.nextTick;
  }
  function nextTickArgs(fn, a, b) {
    process.nextTick(function() {
      fn(a, b);
    });
  }
  return thunky_1;
}
var multicastDns;
var hasRequiredMulticastDns;
function requireMulticastDns() {
  if (hasRequiredMulticastDns) return multicastDns;
  hasRequiredMulticastDns = 1;
  var packet = requireDnsPacket();
  var dgram = require$$1;
  var thunky = requireThunky();
  var events = require$$2;
  var os = require$$0;
  var noop = function() {
  };
  multicastDns = function(opts) {
    if (!opts) opts = {};
    var that = new events.EventEmitter();
    var port = typeof opts.port === "number" ? opts.port : 5353;
    var type = opts.type || "udp4";
    var ip = opts.ip || opts.host || (type === "udp4" ? "224.0.0.251" : null);
    var me = { address: ip, port };
    var memberships = {};
    var destroyed = false;
    var interval = null;
    if (type === "udp6" && (!ip || !opts.interface)) {
      throw new Error("For IPv6 multicast you must specify `ip` and `interface`");
    }
    var socket = opts.socket || dgram.createSocket({
      type,
      reuseAddr: opts.reuseAddr !== false,
      toString: function() {
        return type;
      }
    });
    socket.on("error", function(err) {
      if (err.code === "EACCES" || err.code === "EADDRINUSE") that.emit("error", err);
      else that.emit("warning", err);
    });
    socket.on("message", function(message, rinfo) {
      try {
        message = packet.decode(message);
      } catch (err) {
        that.emit("warning", err);
        return;
      }
      that.emit("packet", message, rinfo);
      if (message.type === "query") that.emit("query", message, rinfo);
      if (message.type === "response") that.emit("response", message, rinfo);
    });
    socket.on("listening", function() {
      if (!port) port = me.port = socket.address().port;
      if (opts.multicast !== false) {
        that.update();
        interval = setInterval(that.update, 5e3);
        socket.setMulticastTTL(opts.ttl || 255);
        socket.setMulticastLoopback(opts.loopback !== false);
      }
    });
    var bind = thunky(function(cb) {
      if (!port || opts.bind === false) return cb(null);
      socket.once("error", cb);
      socket.bind(port, opts.bind || opts.interface, function() {
        socket.removeListener("error", cb);
        cb(null);
      });
    });
    bind(function(err) {
      if (err) return that.emit("error", err);
      that.emit("ready");
    });
    that.send = function(value, rinfo, cb) {
      if (typeof rinfo === "function") return that.send(value, null, rinfo);
      if (!cb) cb = noop;
      if (!rinfo) rinfo = me;
      else if (!rinfo.host && !rinfo.address) rinfo.address = me.address;
      bind(onbind);
      function onbind(err) {
        if (destroyed) return cb();
        if (err) return cb(err);
        var message = packet.encode(value);
        socket.send(message, 0, message.length, rinfo.port, rinfo.address || rinfo.host, cb);
      }
    };
    that.response = that.respond = function(res, rinfo, cb) {
      if (Array.isArray(res)) res = { answers: res };
      res.type = "response";
      res.flags = (res.flags || 0) | packet.AUTHORITATIVE_ANSWER;
      that.send(res, rinfo, cb);
    };
    that.query = function(q, type2, rinfo, cb) {
      if (typeof type2 === "function") return that.query(q, null, null, type2);
      if (typeof type2 === "object" && type2 && type2.port) return that.query(q, null, type2, rinfo);
      if (typeof rinfo === "function") return that.query(q, type2, null, rinfo);
      if (!cb) cb = noop;
      if (typeof q === "string") q = [{ name: q, type: type2 || "ANY" }];
      if (Array.isArray(q)) q = { type: "query", questions: q };
      q.type = "query";
      that.send(q, rinfo, cb);
    };
    that.destroy = function(cb) {
      if (!cb) cb = noop;
      if (destroyed) return process.nextTick(cb);
      destroyed = true;
      clearInterval(interval);
      for (var iface in memberships) {
        try {
          socket.dropMembership(ip, iface);
        } catch (e) {
        }
      }
      memberships = {};
      socket.close(cb);
    };
    that.update = function() {
      var ifaces = opts.interface ? [].concat(opts.interface) : allInterfaces();
      var updated = false;
      for (var i = 0; i < ifaces.length; i++) {
        var addr = ifaces[i];
        if (memberships[addr]) continue;
        try {
          socket.addMembership(ip, addr);
          memberships[addr] = true;
          updated = true;
        } catch (err) {
          that.emit("warning", err);
        }
      }
      if (updated) {
        if (socket.setMulticastInterface) {
          try {
            socket.setMulticastInterface(opts.interface || defaultInterface());
          } catch (err) {
            that.emit("warning", err);
          }
        }
        that.emit("networkInterface");
      }
    };
    return that;
  };
  function defaultInterface() {
    var networks = os.networkInterfaces();
    var names = Object.keys(networks);
    for (var i = 0; i < names.length; i++) {
      var net = networks[names[i]];
      for (var j = 0; j < net.length; j++) {
        var iface = net[j];
        if (isIPv4(iface.family) && !iface.internal) {
          if (os.platform() === "darwin" && names[i] === "en0") return iface.address;
          return "0.0.0.0";
        }
      }
    }
    return "127.0.0.1";
  }
  function allInterfaces() {
    var networks = os.networkInterfaces();
    var names = Object.keys(networks);
    var res = [];
    for (var i = 0; i < names.length; i++) {
      var net = networks[names[i]];
      for (var j = 0; j < net.length; j++) {
        var iface = net[j];
        if (isIPv4(iface.family)) {
          res.push(iface.address);
          break;
        }
      }
    }
    return res;
  }
  function isIPv4(family) {
    return family === 4 || family === "IPv4";
  }
  return multicastDns;
}
var es6;
var hasRequiredEs6;
function requireEs6() {
  if (hasRequiredEs6) return es6;
  hasRequiredEs6 = 1;
  es6 = function equal(a, b) {
    if (a === b) return true;
    if (a && b && typeof a == "object" && typeof b == "object") {
      if (a.constructor !== b.constructor) return false;
      var length, i, keys;
      if (Array.isArray(a)) {
        length = a.length;
        if (length != b.length) return false;
        for (i = length; i-- !== 0; )
          if (!equal(a[i], b[i])) return false;
        return true;
      }
      if (a instanceof Map && b instanceof Map) {
        if (a.size !== b.size) return false;
        for (i of a.entries())
          if (!b.has(i[0])) return false;
        for (i of a.entries())
          if (!equal(i[1], b.get(i[0]))) return false;
        return true;
      }
      if (a instanceof Set && b instanceof Set) {
        if (a.size !== b.size) return false;
        for (i of a.entries())
          if (!b.has(i[0])) return false;
        return true;
      }
      if (ArrayBuffer.isView(a) && ArrayBuffer.isView(b)) {
        length = a.length;
        if (length != b.length) return false;
        for (i = length; i-- !== 0; )
          if (a[i] !== b[i]) return false;
        return true;
      }
      if (a.constructor === RegExp) return a.source === b.source && a.flags === b.flags;
      if (a.valueOf !== Object.prototype.valueOf) return a.valueOf() === b.valueOf();
      if (a.toString !== Object.prototype.toString) return a.toString() === b.toString();
      keys = Object.keys(a);
      length = keys.length;
      if (length !== Object.keys(b).length) return false;
      for (i = length; i-- !== 0; )
        if (!Object.prototype.hasOwnProperty.call(b, keys[i])) return false;
      for (i = length; i-- !== 0; ) {
        var key = keys[i];
        if (!equal(a[key], b[key])) return false;
      }
      return true;
    }
    return a !== a && b !== b;
  };
  return es6;
}
var hasRequiredMdnsServer;
function requireMdnsServer() {
  if (hasRequiredMdnsServer) return mdnsServer;
  hasRequiredMdnsServer = 1;
  var __importDefault = mdnsServer && mdnsServer.__importDefault || function(mod) {
    return mod && mod.__esModule ? mod : { "default": mod };
  };
  Object.defineProperty(mdnsServer, "__esModule", { value: true });
  mdnsServer.Server = void 0;
  const multicast_dns_1 = __importDefault(requireMulticastDns());
  const es6_1 = __importDefault(requireEs6());
  const dns_equal_1 = __importDefault(requireDnsEqual());
  class Server {
    constructor(opts, errorCallback) {
      this.registry = {};
      this.mdns = (0, multicast_dns_1.default)(opts);
      this.mdns.setMaxListeners(0);
      this.mdns.on("query", this.respondToQuery.bind(this));
      this.errorCallback = errorCallback !== null && errorCallback !== void 0 ? errorCallback : function(err) {
        throw err;
      };
    }
    register(records) {
      const shouldRegister = (record) => {
        var subRegistry = this.registry[record.type];
        if (!subRegistry) {
          subRegistry = this.registry[record.type] = [];
        } else if (subRegistry.some(this.isDuplicateRecord(record))) {
          return;
        }
        subRegistry.push(record);
      };
      if (Array.isArray(records)) {
        records.forEach(shouldRegister);
      } else {
        shouldRegister(records);
      }
    }
    unregister(records) {
      const shouldUnregister = (record) => {
        let type = record.type;
        if (!(type in this.registry)) {
          return;
        }
        this.registry[type] = this.registry[type].filter((i) => i.name !== record.name);
      };
      if (Array.isArray(records)) {
        records.forEach(shouldUnregister);
      } else {
        shouldUnregister(records);
      }
    }
    respondToQuery(query) {
      let self = this;
      query.questions.forEach((question) => {
        var type = question.type;
        var name = question.name;
        var answers = type === "ANY" ? Object.keys(self.registry).map(self.recordsFor.bind(self, name)).flat(1) : self.recordsFor(name, type);
        if (answers.length === 0)
          return;
        var additionals = [];
        if (type !== "ANY") {
          answers.forEach((answer) => {
            if (answer.type !== "PTR")
              return;
            additionals = additionals.concat(self.recordsFor(answer.data, "SRV")).concat(self.recordsFor(answer.data, "TXT"));
          });
          additionals.filter(function(record) {
            return record.type === "SRV";
          }).map(function(record) {
            return record.data.target;
          }).filter(this.unique()).forEach(function(target) {
            additionals = additionals.concat(self.recordsFor(target, "A")).concat(self.recordsFor(target, "AAAA"));
          });
        }
        self.mdns.respond({ answers, additionals }, (err) => {
          if (err) {
            this.errorCallback(err);
          }
        });
      });
    }
    recordsFor(name, type) {
      if (!(type in this.registry)) {
        return [];
      }
      return this.registry[type].filter((record) => {
        var _name = ~name.indexOf(".") ? record.name : record.name.split(".")[0];
        return (0, dns_equal_1.default)(_name, name);
      });
    }
    isDuplicateRecord(a) {
      return (b) => {
        return a.type === b.type && a.name === b.name && (0, es6_1.default)(a.data, b.data);
      };
    }
    unique() {
      var set = [];
      return (obj) => {
        if (~set.indexOf(obj))
          return false;
        set.push(obj);
        return true;
      };
    }
  }
  mdnsServer.Server = Server;
  mdnsServer.default = Server;
  return mdnsServer;
}
var browser = {};
var filterService = {};
var hasRequiredFilterService;
function requireFilterService() {
  if (hasRequiredFilterService) return filterService;
  hasRequiredFilterService = 1;
  Object.defineProperty(filterService, "__esModule", { value: true });
  filterService.default = (service2, txtQuery) => {
    if (txtQuery === void 0)
      return true;
    let serviceTxt = service2.txt;
    let query = Object.entries(txtQuery).map(([key, value]) => {
      let queryValue = serviceTxt[key];
      if (queryValue === void 0)
        return false;
      if (value != queryValue)
        return false;
      return true;
    });
    if (query.length == 0)
      return true;
    if (query.includes(false))
      return false;
    return true;
  };
  return filterService;
}
var filterTxt = {};
var hasRequiredFilterTxt;
function requireFilterTxt() {
  if (hasRequiredFilterTxt) return filterTxt;
  hasRequiredFilterTxt = 1;
  Object.defineProperty(filterTxt, "__esModule", { value: true });
  filterTxt.default = (data) => Object.keys(data).filter((key) => !key.includes("binary")).reduce((cur, key) => {
    return Object.assign(cur, { [key]: data[key] });
  }, {});
  return filterTxt;
}
var equalTxt = {};
var hasRequiredEqualTxt;
function requireEqualTxt() {
  if (hasRequiredEqualTxt) return equalTxt;
  hasRequiredEqualTxt = 1;
  Object.defineProperty(equalTxt, "__esModule", { value: true });
  equalTxt.default = equalTxt$1;
  function equalTxt$1(a, b) {
    if (a === void 0 || b === void 0)
      return false;
    let aKeys = Object.keys(a);
    let bKeys = Object.keys(b);
    if (aKeys.length != bKeys.length)
      return false;
    for (let key of aKeys) {
      if (a[key] != b[key])
        return false;
    }
    return true;
  }
  return equalTxt;
}
var hasRequiredBrowser;
function requireBrowser() {
  if (hasRequiredBrowser) return browser;
  hasRequiredBrowser = 1;
  var __importDefault = browser && browser.__importDefault || function(mod) {
    return mod && mod.__esModule ? mod : { "default": mod };
  };
  Object.defineProperty(browser, "__esModule", { value: true });
  browser.Browser = void 0;
  const dns_txt_1 = __importDefault(requireDnsTxt());
  const dns_equal_1 = __importDefault(requireDnsEqual());
  const events_1 = require$$2;
  const service_types_1 = requireServiceTypes();
  const filter_service_1 = __importDefault(requireFilterService());
  const filter_txt_1 = __importDefault(requireFilterTxt());
  const equal_txt_1 = __importDefault(requireEqualTxt());
  const TLD = ".local";
  const WILDCARD = "_services._dns-sd._udp" + TLD;
  class Browser extends events_1.EventEmitter {
    constructor(mdns, opts, onup) {
      super();
      this.onresponse = void 0;
      this.serviceMap = {};
      this.wildcard = false;
      this._services = [];
      if (typeof opts === "function")
        return new Browser(mdns, null, opts);
      this.mdns = mdns;
      this.txt = new dns_txt_1.default(opts !== null && opts.txt != null ? opts.txt : void 0);
      if (opts === null || opts.type === void 0) {
        this.name = WILDCARD;
        this.wildcard = true;
      } else {
        this.name = (0, service_types_1.toString)({ name: opts.type, protocol: opts.protocol || "tcp" }) + TLD;
        if (opts.name)
          this.name = opts.name + "." + this.name;
        this.wildcard = false;
      }
      if (opts != null && opts.txt !== void 0)
        this.txtQuery = (0, filter_txt_1.default)(opts.txt);
      if (onup)
        this.on("up", onup);
      this.start();
    }
    start() {
      if (this.onresponse || this.name === void 0)
        return;
      var self = this;
      var nameMap = {};
      if (!this.wildcard)
        nameMap[this.name] = true;
      this.onresponse = (packet, rinfo) => {
        if (self.wildcard) {
          packet.answers.forEach((answer) => {
            if (answer.type !== "PTR" || answer.name !== self.name || answer.name in nameMap)
              return;
            nameMap[answer.data] = true;
            self.mdns.query(answer.data, "PTR");
          });
        }
        Object.keys(nameMap).forEach(function(name) {
          self.goodbyes(name, packet).forEach(self.removeService.bind(self));
          var matches = self.buildServicesFor(name, packet, self.txt, rinfo);
          if (matches.length === 0)
            return;
          matches.forEach((service2) => {
            if (self.serviceMap[service2.fqdn]) {
              self.updateService(service2);
              return;
            }
            self.addService(service2);
          });
        });
      };
      this.mdns.on("response", this.onresponse);
      this.update();
    }
    stop() {
      if (!this.onresponse)
        return;
      this.mdns.removeListener("response", this.onresponse);
      this.onresponse = void 0;
    }
    update() {
      this.mdns.query(this.name, "PTR");
    }
    get services() {
      return this._services;
    }
    addService(service2) {
      if ((0, filter_service_1.default)(service2, this.txtQuery) === false)
        return;
      this._services.push(service2);
      this.serviceMap[service2.fqdn] = true;
      this.emit("up", service2);
    }
    updateService(service2) {
      var _a;
      if ((0, equal_txt_1.default)(service2.txt, ((_a = this._services.find((s) => (0, dns_equal_1.default)(s.fqdn, service2.fqdn))) === null || _a === void 0 ? void 0 : _a.txt) || {}))
        return;
      if (!(0, filter_service_1.default)(service2, this.txtQuery)) {
        this.removeService(service2.fqdn);
        return;
      }
      this._services = this._services.map(function(s) {
        if (!(0, dns_equal_1.default)(s.fqdn, service2.fqdn))
          return s;
        return service2;
      });
      this.emit("txt-update", service2);
    }
    removeService(fqdn) {
      var service2, index2;
      this._services.some(function(s, i) {
        if ((0, dns_equal_1.default)(s.fqdn, fqdn)) {
          service2 = s;
          index2 = i;
          return true;
        }
      });
      if (!service2 || index2 === void 0)
        return;
      this._services.splice(index2, 1);
      delete this.serviceMap[fqdn];
      this.emit("down", service2);
    }
    goodbyes(name, packet) {
      return packet.answers.concat(packet.additionals).filter((rr) => rr.type === "PTR" && rr.ttl === 0 && (0, dns_equal_1.default)(rr.name, name)).map((rr) => rr.data);
    }
    buildServicesFor(name, packet, txt, referer) {
      var records = packet.answers.concat(packet.additionals).filter((rr) => rr.ttl > 0);
      return records.filter((rr) => rr.type === "PTR" && (0, dns_equal_1.default)(rr.name, name)).map((ptr) => {
        const service2 = {
          addresses: [],
          subtypes: []
        };
        records.filter((rr) => {
          return rr.type === "PTR" && (0, dns_equal_1.default)(rr.data, ptr.data) && rr.name.includes("._sub");
        }).forEach((rr) => {
          const types2 = (0, service_types_1.toType)(rr.name);
          service2.subtypes.push(types2.subtype);
        });
        records.filter((rr) => {
          return (rr.type === "SRV" || rr.type === "TXT") && (0, dns_equal_1.default)(rr.name, ptr.data);
        }).forEach((rr) => {
          if (rr.type === "SRV") {
            var parts = rr.name.split(".");
            var name2 = parts[0];
            var types2 = (0, service_types_1.toType)(parts.slice(1, -1).join("."));
            service2.name = name2;
            service2.fqdn = rr.name;
            service2.host = rr.data.target;
            service2.referer = referer;
            service2.port = rr.data.port;
            service2.type = types2.name;
            service2.protocol = types2.protocol;
          } else if (rr.type === "TXT") {
            service2.rawTxt = rr.data;
            service2.txt = this.txt.decodeAll(rr.data);
          }
        });
        if (!service2.name)
          return;
        records.filter((rr) => (rr.type === "A" || rr.type === "AAAA") && (0, dns_equal_1.default)(rr.name, service2.host)).forEach((rr) => service2.addresses.push(rr.data));
        return service2;
      }).filter((rr) => !!rr);
    }
  }
  browser.Browser = Browser;
  browser.default = Browser;
  return browser;
}
var hasRequiredDist;
function requireDist() {
  if (hasRequiredDist) return dist;
  hasRequiredDist = 1;
  var __importDefault = dist && dist.__importDefault || function(mod) {
    return mod && mod.__esModule ? mod : { "default": mod };
  };
  Object.defineProperty(dist, "__esModule", { value: true });
  dist.Browser = dist.Service = dist.Bonjour = void 0;
  const registry_1 = __importDefault(requireRegistry());
  const mdns_server_1 = __importDefault(requireMdnsServer());
  const browser_1 = __importDefault(requireBrowser());
  dist.Browser = browser_1.default;
  const service_1 = __importDefault(requireService());
  dist.Service = service_1.default;
  class Bonjour {
    constructor(opts = {}, errorCallback) {
      this.server = new mdns_server_1.default(opts, errorCallback);
      this.registry = new registry_1.default(this.server);
    }
    publish(opts) {
      return this.registry.publish(opts);
    }
    unpublishAll(callback) {
      return this.registry.unpublishAll(callback);
    }
    find(opts = null, onup) {
      return new browser_1.default(this.server.mdns, opts, onup);
    }
    findOne(opts = null, timeout = 1e4, callback) {
      const browser2 = new browser_1.default(this.server.mdns, opts);
      var timer;
      browser2.once("up", (service2) => {
        if (timer !== void 0)
          clearTimeout(timer);
        browser2.stop();
        if (callback)
          callback(service2);
      });
      timer = setTimeout(() => {
        browser2.stop();
        if (callback)
          callback(null);
      }, timeout);
      return browser2;
    }
    destroy(callback) {
      this.registry.destroy();
      this.server.mdns.destroy(callback);
    }
  }
  dist.Bonjour = Bonjour;
  dist.default = Bonjour;
  return dist;
}
var distExports = requireDist();
const index = /* @__PURE__ */ getDefaultExportFromCjs(distExports);
const index$1 = /* @__PURE__ */ _mergeNamespaces({
  __proto__: null,
  default: index
}, [distExports]);
export {
  index$1 as i
};
