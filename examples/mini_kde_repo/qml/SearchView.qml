// SPDX-License-Identifier: LGPL-2.1-or-later
import QtQuick 2.15
import QtQuick.Controls 2.15
import org.kde.minisearch 1.0

ApplicationWindow {
    id: root
    title: "MiniSearch"
    width: 800
    height: 600
    visible: true

    KFileSearcher {
        id: searcher
        maxResults: 100
        onResultsReady: function(paths) { resultsModel.clear(); for (var i in paths) resultsModel.append({"path": paths[i]}); }
        onSearchFailed: function(reason) { statusLabel.text = "Failed: " + reason; }
    }

    Column {
        anchors.fill: parent
        spacing: 8

        Row {
            spacing: 8
            TextField {
                id: pathField
                placeholderText: "/path/to/scan"
                width: 400
            }
            TextField {
                id: queryField
                placeholderText: "filename substring"
                width: 200
            }
            Button {
                text: "Search"
                onClicked: searcher.searchPath(pathField.text, queryField.text)
            }
            Button {
                text: "Cancel"
                onClicked: searcher.cancel()
            }
        }

        Label { id: statusLabel; text: "Ready" }

        ListView {
            width: parent.width
            height: parent.height - 100
            model: ListModel { id: resultsModel }
            delegate: Text { text: path }
        }
    }
}
