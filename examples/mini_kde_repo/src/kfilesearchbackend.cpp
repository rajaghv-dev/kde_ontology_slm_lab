// SPDX-License-Identifier: LGPL-2.1-or-later
#include "kfilesearchbackend.h"

#include <QDir>
#include <QDirIterator>
#include <QLoggingCategory>

Q_LOGGING_CATEGORY(MINISEARCH_BACKEND, "minisearch.backend")

KFileSearchBackend::KFileSearchBackend(QObject *parent)
    : QObject(parent)
{}

void KFileSearchBackend::scanDirectory(const QString &path, const QString &query, int maxResults)
{
    m_cancelled = false;
    qCDebug(MINISEARCH_BACKEND) << "scanDirectory" << path << "query=" << query << "max=" << maxResults;

    QStringList results;
    QDirIterator it(path, QDir::Files, QDirIterator::Subdirectories);
    int processed = 0;
    while (it.hasNext() && !m_cancelled) {
        const QString p = it.next();
        ++processed;
        if (p.contains(query, Qt::CaseInsensitive)) {
            results << p;
            if (results.size() >= maxResults) break;
        }
        if (processed % 500 == 0) {
            Q_EMIT scanProgress(processed);
        }
    }

    if (m_cancelled) {
        Q_EMIT scanFailed(QStringLiteral("Scan cancelled by user"));
        return;
    }

    qCDebug(MINISEARCH_BACKEND) << "scan complete processed=" << processed << "hits=" << results.size();
    Q_EMIT scanCompleted(results);
}

void KFileSearchBackend::cancelScan()
{
    m_cancelled = true;
}
