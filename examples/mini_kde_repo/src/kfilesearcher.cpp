// SPDX-License-Identifier: LGPL-2.1-or-later
#include "kfilesearcher.h"
#include "kfilesearchbackend.h"

#include <QDebug>
#include <KConfigGroup>
#include <KSharedConfig>

KFileSearcher::KFileSearcher(QObject *parent)
    : QObject(parent)
    , m_backend(new KFileSearchBackend(this))
    , m_maxResults(100)
{
    auto cfg = KSharedConfig::openConfig(QStringLiteral("minisearchrc"));
    KConfigGroup grp(cfg, QStringLiteral("Search"));
    m_maxResults = grp.readEntry("MaxResults", 100);

    connect(m_backend, &KFileSearchBackend::scanCompleted,
            this, &KFileSearcher::resultsReady);
    connect(m_backend, &KFileSearchBackend::scanFailed,
            this, &KFileSearcher::searchFailed);
}

KFileSearcher::~KFileSearcher() = default;

QString KFileSearcher::currentPath() const { return m_currentPath; }

void KFileSearcher::setCurrentPath(const QString &path)
{
    if (path == m_currentPath) return;
    m_currentPath = path;
    Q_EMIT currentPathChanged(path);
}

int KFileSearcher::maxResults() const { return m_maxResults; }

void KFileSearcher::setMaxResults(int n)
{
    if (n == m_maxResults) return;
    m_maxResults = n;
    Q_EMIT maxResultsChanged(n);
}

void KFileSearcher::searchPath(const QString &path, const QString &query)
{
    setCurrentPath(path);
    qDebug() << "KFileSearcher::searchPath" << path << query << "maxResults=" << m_maxResults;
    m_backend->scanDirectory(path, query, m_maxResults);
}

void KFileSearcher::cancel()
{
    m_backend->cancelScan();
}
