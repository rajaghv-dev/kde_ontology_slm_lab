// SPDX-License-Identifier: LGPL-2.1-or-later
#ifndef MINISEARCH_KFILESEARCHBACKEND_H
#define MINISEARCH_KFILESEARCHBACKEND_H

#include <QObject>
#include <QStringList>

class KFileSearchBackend : public QObject
{
    Q_OBJECT
public:
    explicit KFileSearchBackend(QObject *parent = nullptr);

public Q_SLOTS:
    void scanDirectory(const QString &path, const QString &query, int maxResults);
    void cancelScan();

Q_SIGNALS:
    void scanCompleted(const QStringList &paths);
    void scanFailed(const QString &reason);
    void scanProgress(int filesProcessed);

private:
    bool m_cancelled = false;
};

#endif
