(function () {
  function setText(node, value) {
    node.textContent = value == null ? "" : String(value);
  }

  function emptyRow(columns, message) {
    var row = document.createElement("tr");
    var cell = document.createElement("td");
    cell.colSpan = columns;
    cell.className = "empty";
    setText(cell, message);
    row.appendChild(cell);
    return row;
  }

  function renderCpu(cpu) {
    var node = document.getElementById("cpu-value");
    if (!cpu || cpu.error) {
      setText(node, cpu && cpu.error ? cpu.error : "Unavailable");
      return;
    }
    if (cpu.text) {
      setText(node, cpu.text);
      return;
    }
    setText(node, String(cpu.percent) + "%");
  }

  function renderMemory(memory) {
    var node = document.getElementById("memory-value");
    node.replaceChildren();
    node.classList.remove("empty");
    if (!memory || memory.error) {
      node.classList.add("empty");
      setText(node, memory && memory.error ? memory.error : "Unavailable");
      return;
    }
    var lines = [
      ["Total", memory.total_kb + " kB"],
      ["Available", memory.available_kb + " kB"],
      ["Used", memory.used_kb + " kB"],
      ["Used percent", memory.used_percent + "%"]
    ];
    lines.forEach(function (pair) {
      var paragraph = document.createElement("p");
      var label = document.createElement("span");
      var value = document.createElement("span");
      setText(label, pair[0] + ": ");
      setText(value, pair[1]);
      paragraph.appendChild(label);
      paragraph.appendChild(value);
      node.appendChild(paragraph);
    });
  }

  function renderNetwork(network) {
    var body = document.getElementById("network-body");
    body.replaceChildren();
    if (!network || network.error) {
      body.appendChild(emptyRow(5, network && network.error ? network.error : "Unavailable"));
      return;
    }
    if (!network.length) {
      body.appendChild(emptyRow(5, "No interfaces"));
      return;
    }
    network.forEach(function (iface) {
      var row = document.createElement("tr");
      [iface.name, iface.received_bytes, iface.transmitted_bytes, rate(iface.rx_per_sec), rate(iface.tx_per_sec)].forEach(function (value) {
        var cell = document.createElement("td");
        setText(cell, value);
        row.appendChild(cell);
      });
      body.appendChild(row);
    });
  }

  function rate(value) {
    return value == null ? "Collecting…" : String(value);
  }

  function renderPorts(ports) {
    var body = document.getElementById("ports-body");
    body.replaceChildren();
    if (!ports || ports.error) {
      body.appendChild(emptyRow(3, ports && ports.error ? ports.error : "Unavailable"));
      return;
    }
    if (!ports.length) {
      body.appendChild(emptyRow(3, "No listening ports"));
      return;
    }
    ports.forEach(function (entry) {
      var row = document.createElement("tr");
      [entry.protocol, entry.port, entry.process || ""].forEach(function (value) {
        var cell = document.createElement("td");
        setText(cell, value);
        row.appendChild(cell);
      });
      body.appendChild(row);
    });
  }

  function render(data) {
    renderCpu(data.cpu);
    renderMemory(data.memory);
    renderNetwork(data.network);
    renderPorts(data.ports);
  }

  function tick() {
    fetch("/metrics", { headers: { Accept: "application/json" } })
      .then(function (response) {
        if (!response.ok) {
          throw new Error("metrics failed");
        }
        return response.json();
      })
      .then(render)
      .catch(function () {
        setText(document.getElementById("cpu-value"), "Unavailable");
      });
  }

  tick();
  setInterval(tick, 5000);
})();
