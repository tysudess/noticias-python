import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: root
    width: 412
    height: 915
    visible: true
    title: "Central Inteligente de Mídia"
    color: "#07101f"

    property string currentSection: appBridge.currentSection

    readonly property var modules: [
        { "title": "Notícias", "subtitle": "Monitoramento e matérias", "icon": "N", "accent": "#42d9ff" },
        { "title": "Vídeos", "subtitle": "Fontes e conteúdos", "icon": "V", "accent": "#ff5470" },
        { "title": "Demandas", "subtitle": "Fila de trabalho", "icon": "D", "accent": "#35e6ad" },
        { "title": "Capas", "subtitle": "Jornais e destaques", "icon": "C", "accent": "#e967d5" },
        { "title": "Extrator", "subtitle": "Extrair mídia", "icon": "E", "accent": "#50e4de" },
        { "title": "PDF", "subtitle": "Ferramentas PDF", "icon": "P", "accent": "#ff6a82" },
        { "title": "Histórico", "subtitle": "Atividades recentes", "icon": "H", "accent": "#ffb52e" },
        { "title": "Configurações", "subtitle": "Sistema e proxy", "icon": "⚙", "accent": "#a978ff" }
    ]

    component GlassCard: Rectangle {
        radius: 22
        color: "#111c31"
        border.color: "#253754"
        border.width: 1
    }

    component NavButton: Item {
        id: nav
        property string label
        property string glyph
        property bool active: false
        signal pressed()

        implicitWidth: 92
        implicitHeight: 58

        Rectangle {
            anchors.fill: parent
            radius: 18
            color: nav.active ? "#17314c" : "transparent"
            border.color: nav.active ? "#36d7ff" : "transparent"
            border.width: nav.active ? 1 : 0
        }

        Column {
            anchors.centerIn: parent
            spacing: 2

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: nav.glyph
                color: nav.active ? "#55e4ff" : "#8396b4"
                font.pixelSize: 18
                font.bold: true
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: nav.label
                color: nav.active ? "#eaf8ff" : "#8396b4"
                font.pixelSize: 11
                font.weight: nav.active ? Font.DemiBold : Font.Normal
            }
        }

        TapHandler { onTapped: nav.pressed() }
    }

    background: Rectangle {
        color: "#07101f"

        Rectangle {
            width: parent.width * 1.25
            height: width
            radius: width / 2
            x: -width * 0.46
            y: -height * 0.58
            color: "#102847"
            opacity: 0.72
        }

        Rectangle {
            width: parent.width * 0.9
            height: width
            radius: width / 2
            x: parent.width * 0.62
            y: parent.height * 0.15
            color: "#142348"
            opacity: 0.48
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 14

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 72

            RowLayout {
                anchors.fill: parent
                spacing: 12

                Rectangle {
                    Layout.preferredWidth: 48
                    Layout.preferredHeight: 48
                    radius: 15
                    color: "#132b44"
                    border.color: "#35d8ff"

                    Text {
                        anchors.centerIn: parent
                        text: "C"
                        color: "#66e7ff"
                        font.pixelSize: 22
                        font.bold: true
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 1

                    Text {
                        text: "CENTRAL INTELIGENTE"
                        color: "#f4f8ff"
                        font.pixelSize: 17
                        font.bold: true
                        font.letterSpacing: 0.5
                    }

                    Text {
                        text: "DE MÍDIA  •  ANDROID"
                        color: "#7187a8"
                        font.pixelSize: 11
                        font.weight: Font.Medium
                        font.letterSpacing: 1.0
                    }
                }

                Rectangle {
                    Layout.preferredWidth: 43
                    Layout.preferredHeight: 43
                    radius: 14
                    color: "#101c30"
                    border.color: "#253754"

                    Text {
                        anchors.centerIn: parent
                        text: "⋮"
                        color: "#c5d5ec"
                        font.pixelSize: 24
                    }
                }
            }
        }

        Flickable {
            id: content
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            contentWidth: width
            contentHeight: contentColumn.implicitHeight + 20

            Column {
                id: contentColumn
                width: content.width
                spacing: 14

                GlassCard {
                    width: parent.width
                    height: 190

                    Column {
                        anchors.fill: parent
                        anchors.margins: 20
                        spacing: 12

                        Row {
                            width: parent.width
                            spacing: 8

                            Rectangle {
                                width: 9
                                height: 9
                                radius: 5
                                color: "#37e4ad"
                                anchors.verticalCenter: parent.verticalCenter

                                SequentialAnimation on opacity {
                                    loops: Animation.Infinite
                                    NumberAnimation { from: 1; to: 0.35; duration: 900 }
                                    NumberAnimation { from: 0.35; to: 1; duration: 900 }
                                }
                            }

                            Text {
                                text: "MONITORAMENTO"
                                color: "#8fa5c4"
                                font.pixelSize: 12
                                font.bold: true
                                font.letterSpacing: 1.2
                            }
                        }

                        Text {
                            text: root.currentSection === "Início" ? "Sistema pronto" : root.currentSection
                            color: "#f7fbff"
                            font.pixelSize: 29
                            font.bold: true
                        }

                        Text {
                            width: parent.width
                            text: root.currentSection === "Início"
                                  ? "A versão mobile está preparada para receber os módulos da Central sem alterar o aplicativo Windows."
                                  : "Módulo selecionado. A integração funcional será conectada nas próximas etapas."
                            color: "#91a5c2"
                            font.pixelSize: 13
                            wrapMode: Text.WordWrap
                            lineHeight: 1.2
                        }

                        Row {
                            spacing: 9

                            Rectangle {
                                width: 108
                                height: 32
                                radius: 16
                                color: "#123b3a"
                                border.color: "#2bd6a7"

                                Text {
                                    anchors.centerIn: parent
                                    text: "● ONLINE"
                                    color: "#4be5b9"
                                    font.pixelSize: 11
                                    font.bold: true
                                }
                            }

                            Rectangle {
                                width: 128
                                height: 32
                                radius: 16
                                color: "#142944"
                                border.color: "#31557d"

                                Text {
                                    anchors.centerIn: parent
                                    text: appBridge.versionLabel()
                                    color: "#9fc9ef"
                                    font.pixelSize: 11
                                    font.bold: true
                                }
                            }
                        }
                    }
                }

                Row {
                    width: parent.width

                    Text {
                        text: "Módulos"
                        color: "#f1f6ff"
                        font.pixelSize: 20
                        font.bold: true
                    }

                    Item { width: parent.width - 130; height: 1 }

                    Text {
                        text: "Toque para abrir"
                        color: "#7187a8"
                        font.pixelSize: 11
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }

                Grid {
                    width: parent.width
                    columns: 2
                    columnSpacing: 12
                    rowSpacing: 12

                    Repeater {
                        model: root.modules

                        delegate: GlassCard {
                            required property var modelData
                            width: (contentColumn.width - 12) / 2
                            height: 132

                            Rectangle {
                                x: 14
                                y: 14
                                width: 42
                                height: 42
                                radius: 13
                                color: Qt.rgba(0.08, 0.14, 0.24, 1)
                                border.color: modelData.accent

                                Text {
                                    anchors.centerIn: parent
                                    text: modelData.icon
                                    color: modelData.accent
                                    font.pixelSize: 17
                                    font.bold: true
                                }
                            }

                            Text {
                                x: 14
                                y: 66
                                width: parent.width - 28
                                text: modelData.title
                                color: "#f5f9ff"
                                font.pixelSize: 15
                                font.bold: true
                                elide: Text.ElideRight
                            }

                            Text {
                                x: 14
                                y: 91
                                width: parent.width - 28
                                text: modelData.subtitle
                                color: "#778ba8"
                                font.pixelSize: 11
                                elide: Text.ElideRight
                            }

                            TapHandler {
                                onTapped: appBridge.openSection(modelData.title)
                            }
                        }
                    }
                }

                Item { width: 1; height: 8 }
            }
        }

        GlassCard {
            Layout.fillWidth: true
            Layout.preferredHeight: 72

            RowLayout {
                anchors.fill: parent
                anchors.margins: 7
                spacing: 2

                NavButton {
                    Layout.fillWidth: true
                    label: "Início"
                    glyph: "⌂"
                    active: root.currentSection === "Início"
                    onPressed: appBridge.openSection("Início")
                }

                NavButton {
                    Layout.fillWidth: true
                    label: "Notícias"
                    glyph: "N"
                    active: root.currentSection === "Notícias"
                    onPressed: appBridge.openSection("Notícias")
                }

                NavButton {
                    Layout.fillWidth: true
                    label: "Demandas"
                    glyph: "D"
                    active: root.currentSection === "Demandas"
                    onPressed: appBridge.openSection("Demandas")
                }

                NavButton {
                    Layout.fillWidth: true
                    label: "Mais"
                    glyph: "•••"
                    active: root.currentSection !== "Início"
                            && root.currentSection !== "Notícias"
                            && root.currentSection !== "Demandas"
                    onPressed: appBridge.openSection("Configurações")
                }
            }
        }
    }
}
