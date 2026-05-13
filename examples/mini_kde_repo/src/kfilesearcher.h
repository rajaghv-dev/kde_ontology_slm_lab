// SPDX-License-Identifier: LGPL-2.1-or-later
// Mini KDE-style header. Not real KDE — fixture for kde_ontology_slm_lab.
#ifndef MINISEARCH_KFILESEARCHER_H
#define MINISEARCH_KFILESEARCHER_H

#include <QObject>
#include <QString>
#include <QStringList>

class KFileSearchBackend;

class KFileSearcher : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QString currentPath READ currentPath WRITE setCurrentPath NOTIFY currentPathChanged)
    Q_PROPERTY(int maxResults READ maxResults WRITE setMaxResults NOTIFY maxResultsChanged)

public:
    explicit KFileSearcher(QObject *parent = nullptr);
    ~KFileSearcher() override;

    QString currentPath() const;
    void setCurrentPath(const QString &path);

    int maxResults() const;
    void setMaxResults(int n);

public Q_SLOTS:
    void searchPath(const QString &path, const QString &query);
    void cancel();

Q_SIGNALS:
    void currentPathChanged(const QString &path);
    void maxResultsChanged(int n);
    void resultsReady(const QStringList &paths);
    void searchFailed(const QString &reason);

private:
    KFileSearchBackend *m_backend;
    QString m_currentPath;
    int m_maxResults;
};

#endif
