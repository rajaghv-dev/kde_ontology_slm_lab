// SPDX-License-Identifier: LGPL-2.1-or-later
#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include <qqml.h>

#include "kfilesearcher.h"

int main(int argc, char *argv[])
{
    QGuiApplication app(argc, argv);

    qmlRegisterType<KFileSearcher>("org.kde.minisearch", 1, 0, "KFileSearcher");

    QQmlApplicationEngine engine;
    engine.load(QUrl(QStringLiteral("qrc:/qml/SearchView.qml")));
    if (engine.rootObjects().isEmpty()) return -1;
    return app.exec();
}
