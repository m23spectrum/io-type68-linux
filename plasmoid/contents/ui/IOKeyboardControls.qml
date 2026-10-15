// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Layouts
import QtQuick.Dialogs
import org.kde.plasma.components as PC
import org.kde.kirigami as Kirigami
import org.kde.plasma.workspace.dbus as DBus

ColumnLayout {
    id: root
    property var state: ({connected: false})
    property bool busy: false
    property string message: ""
    property bool advanced: false
    property var selected: []
    property var colorKeys: []
    readonly property bool available: state.connected === true
    readonly property var lighting: state.lighting || ({brightness: 0, mode: 1, color: "#ffffff", speed: 3, colorMode: 0, direction: 0})
    readonly property var effect: state.effect || ({mode: "none"})
    readonly property var modes: ["Выключена", "Постоянный цвет", "Подсветка нажатия", "Гашение при нажатии", "Звёзды", "Снег", "Цветы", "Дыхание", "Спектр", "Фонтан", "Перекрёстные волны", "Волна", "Горная волна", "Вспышка", "Двойная волна", "Рябь", "Поток", "Каскад", "Дождь", "Маятник", "Цвет каждой клавиши"]
    spacing: Kirigami.Units.smallSpacing
    visible: true

    function call(member, args, callback) {
        if (busy) return;
        busy = true;
        const reply = DBus.SessionBus.asyncCall({service: "local.io.Keyboard", path: "/local/io/Keyboard", iface: "local.io.Keyboard", member: member, arguments: args});
        let handled = false;
        const finish = function() {
            if (handled) return;
            handled = true;
            busy = false;
            if (reply.isError) { message = reply.error.message; return; }
            try { callback(JSON.parse(reply.value)); } catch(e) { message = String(e); }
        };
        if (reply.isFinished) finish(); else reply.finished.connect(finish);
    }
    function refresh() {
        call("Snapshot", [], function(s) { root.state = s; if (!s.connected) root.message = s.error || "Клавиатура отключена"; });
    }
    function apply(kind, values) {
        call("Apply", [JSON.stringify({kind: kind, values: values, selected: kind === "lighting" ? [] : selected})], function(result) {
            if (result.ok) { root.state = result.state; root.message = kind === "effect" || root.effect.mode !== "none" ? "Программный эффект обновлён" : "Сохранено в клавиатуре ✓"; }
            else root.message = result.error;
        });
    }
    function allKeys() { return (state.keys || []).reduce((a,row)=>a.concat(row.map(k=>k.value)), []); }
    function choose(values) {
        selected = values;
        const keys = (state.keys || []).reduce((a,row)=>a.concat(row), []);
        const first = keys.find(k=>values.indexOf(k.value)>=0);
        if (first) { trigger.value = Math.round(first.trigger*100); rapid.checked = first.rapid; press.value=Math.max(10,Math.round(first.press*100)); release.value=Math.max(10,Math.round(first.release*100)); }
    }
    Component.onCompleted: refresh()
    DBus.Properties {
        id: liveState
        busType: DBus.BusType.Session
        service: "local.io.Keyboard"
        path: "/local/io/Keyboard"
        iface: "local.io.Keyboard"
    }
    readonly property string liveStateJson: liveState.properties.State || ""
    onLiveStateJsonChanged: {
        if (liveStateJson.length) {
            try { root.state = JSON.parse(liveStateJson); } catch(e) { root.message = String(e); }
        }
    }
    Timer { interval: 5000; repeat: true; running: root.visible; onTriggered: root.refresh() }

    RowLayout {
        Layout.fillWidth: true
        Kirigami.Icon { source: "input-keyboard"; Layout.preferredWidth: 24; Layout.preferredHeight: 24 }
        PC.Label { text: "IO Type 68 Magnetic"; font.bold: true; Layout.fillWidth: true }
        PC.Label { text: Math.round(root.lighting.brightness * 20) + "%" }
    }
    PC.ComboBox {
        Layout.fillWidth: true
        model: ["Без программного эффекта", "Северное сияние", "Мягкое дыхание", "Комета", "Радужная волна"]
        property var values: ["none", "aurora", "breathing", "comet", "rainbow"]
        currentIndex: values.indexOf(root.effect.mode)
        Accessible.name: "Новые эффекты клавиатуры"
        enabled: !root.busy
        onActivated: root.apply("effect", {mode: values[currentIndex], color: root.lighting.color, speed: root.lighting.speed})
    }
    PC.Label { text: "Программная анимация до 30 кадров/с; работает, пока запущена служба."; visible: root.effect.mode !== "none"; opacity: .7; wrapMode: Text.WordWrap; Layout.fillWidth: true }
    PC.Label { text: root.effect.error || ""; visible: text.length>0; color: Kirigami.Theme.negativeTextColor; wrapMode: Text.WordWrap; Layout.fillWidth: true }
    PC.Slider {
        id: brightness
        Layout.fillWidth: true
        from: 0; to: 5; stepSize: 1; snapMode: PC.Slider.SnapAlways
        value: root.lighting.brightness
        enabled: root.available && !root.busy
        Accessible.name: "Яркость IO Type 68 Magnetic"
        onMoved: if (!pressed) root.apply("lighting", {brightness: Math.round(value)})
        property bool dragStarted: false
        onPressedChanged: { if (pressed) dragStarted = true; else if (dragStarted) { dragStarted = false; root.apply("lighting", {brightness: Math.round(value)}); } }
    }
    RowLayout {
        Layout.fillWidth: true
        PC.ComboBox {
            Layout.fillWidth: true
            model: root.modes
            currentIndex: root.lighting.mode === 128 ? 20 : root.lighting.mode
            enabled: !root.busy
            Accessible.name: "Эффект подсветки"
            onActivated: root.apply("lighting", {mode: currentIndex === 20 ? 128 : currentIndex})
        }
        PC.Button { text: "Цвет…"; enabled: !root.busy; onClicked: { root.colorKeys = []; colorDialog.selectedColor = root.lighting.color; colorDialog.open(); } }
        Rectangle { width: 22; height: 22; radius: 11; color: root.lighting.color; border.color: Kirigami.Theme.textColor }
    }
    PC.Label { text: root.effect.mode === "none" ? "Выбор цвета включает постоянную подсветку." : "Выбор цвета меняет палитру программного эффекта."; opacity: .7; Layout.fillWidth: true; wrapMode: Text.WordWrap }
    ColorDialog {
        id: colorDialog
        title: "Цвет клавиатуры"
        onAccepted: root.call("Apply", [JSON.stringify({kind: "lighting", values: {color: selectedColor.toString()}, selected: root.colorKeys})], function(result) {
            if (result.ok) { root.state = result.state; root.message = "Цвет сохранён в клавиатуре ✓"; }
            else root.message = result.error;
        })
    }
    RowLayout {
        Layout.fillWidth: true
        PC.ComboBox { model: ["→", "←", "↓", "↑"]; currentIndex: root.lighting.direction; enabled: !root.busy; Accessible.name: "Направление эффекта"; onActivated: root.apply("lighting", {direction: currentIndex}) }
        PC.Label { text: "Скорость" }
        PC.Slider { Layout.fillWidth: true; from: 1; to: 5; stepSize: 1; value: root.lighting.speed; enabled: !root.busy; Accessible.name: "Скорость эффекта"; property bool dragStarted: false; onPressedChanged: { if (pressed) dragStarted = true; else if (dragStarted) { dragStarted = false; root.apply("lighting", {speed: Math.round(value)}); } } }
    }
    PC.Button {
        Layout.fillWidth: true
        text: root.advanced ? "Скрыть настройки магнитных клавиш ▴" : "Точка срабатывания и Rapid Trigger ▾"
        enabled: root.available && !root.busy
        onClicked: {
            root.advanced = !root.advanced;
            if (root.advanced) root.call("RefreshKeys", [], function(s) { root.state = s; if (root.advanced) root.choose(root.allKeys()); });
        }
    }
    ColumnLayout {
        visible: root.advanced
        Layout.fillWidth: true
        spacing: Kirigami.Units.smallSpacing
        RowLayout {
            PC.Button { text: "Все клавиши"; onClicked: root.choose(root.allKeys()) }
            PC.Button { text: "WASD"; onClicked: root.choose([34,49,50,51]) }
            PC.Label { text: "Выбрано: " + root.selected.length; Layout.fillWidth: true }
        }
        Repeater {
            model: root.state.keys || []
            RowLayout {
                required property var modelData
                Layout.fillWidth: true
                spacing: 1
                Repeater {
                    model: modelData
                    PC.Button {
                        required property var modelData
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        leftPadding: 1; rightPadding: 1
                        text: modelData.name.split(" ")[0]
                        font.pixelSize: 10
                        checkable: true
                        checked: root.selected.indexOf(modelData.value) >= 0
                        Accessible.name: modelData.name + ", " + modelData.trigger.toFixed(2) + " мм"
                        onClicked: root.choose([modelData.value])
                    }
                }
            }
        }
        PC.Label { text: "Глубина срабатывания выбранных клавиш"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
        RowLayout {
            Layout.fillWidth: true
            PC.SpinBox { id: trigger; from: 10; to: 320; stepSize: 1; value: 120; editable: true; textFromValue: v=>(v/100).toFixed(2) + " мм"; valueFromText: t=>Math.round(parseFloat(t.replace(",", "."))*100); Layout.fillWidth: true; Accessible.name: "Глубина срабатывания" }
            PC.Button { text: "Применить глубину"; enabled: !root.busy && root.selected.length>0; onClicked: root.apply("keys", {trigger: trigger.value/100}) }
        }
        PC.CheckBox { id: rapid; text: "Rapid Trigger для выбранных клавиш" }
        RowLayout {
            PC.Label { text: "Нажатие / отпускание" }
            PC.SpinBox { id: press; from: 10; to: 320; value: 10; stepSize: 1; editable: true; textFromValue: v=>(v/100).toFixed(2); valueFromText: t=>Math.round(parseFloat(t.replace(",", "."))*100); Layout.fillWidth: true; Accessible.name: "Rapid Trigger: нажатие, мм" }
            PC.SpinBox { id: release; from: 10; to: 320; value: 10; stepSize: 1; editable: true; textFromValue: v=>(v/100).toFixed(2); valueFromText: t=>Math.round(parseFloat(t.replace(",", "."))*100); Layout.fillWidth: true; Accessible.name: "Rapid Trigger: отпускание, мм" }
        }
        PC.Button { text: "Применить Rapid Trigger"; Layout.fillWidth: true; enabled: !root.busy && root.selected.length>0; onClicked: root.apply("keys", rapid.checked ? {rapid: true, press: press.value/100, release: release.value/100} : {rapid: false}) }
        PC.Button { text: "Цвет выбранных клавиш…"; Layout.fillWidth: true; enabled: !root.busy && root.selected.length>0; onClicked: { root.colorKeys = root.selected.slice(); colorDialog.selectedColor = root.lighting.color; colorDialog.open(); } }
        RowLayout {
            PC.Label { text: "Мёртвые зоны, мм: верх / низ" }
            PC.SpinBox { id: topZone; from: 0; to: 50; value: Math.round((root.state.topDeadZone || 0)*100); editable: true; textFromValue: v=>(v/100).toFixed(2); valueFromText: t=>Math.round(parseFloat(t.replace(",", "."))*100); Layout.fillWidth: true }
            PC.SpinBox { id: bottomZone; from: 0; to: 50; value: Math.round((root.state.bottomDeadZone || 0)*100); editable: true; textFromValue: v=>(v/100).toFixed(2); valueFromText: t=>Math.round(parseFloat(t.replace(",", "."))*100); Layout.fillWidth: true }
        }
        PC.Button { text: "Применить мёртвые зоны"; Layout.fillWidth: true; enabled: !root.busy; onClicked: root.apply("deadzone", {topDeadZone: topZone.value/100, bottomDeadZone: bottomZone.value/100}) }
        PC.Label { text: "Значения в мм. Глубина и Rapid Trigger сохраняются отдельно."; wrapMode: Text.WordWrap; opacity: .7; Layout.fillWidth: true }
    }
    PC.Label { text: root.message; visible: text.length>0; wrapMode: Text.WordWrap; Layout.fillWidth: true; color: root.available ? Kirigami.Theme.textColor : Kirigami.Theme.negativeTextColor }
}
