///New Ticket Minuimum Version
Issues.create('DS', 'Task') {
    setSummary('My Issue Summary')
    setPriority('High')
    setDescription('Some description')
}

////New Ticket - Mode details including Custom Field
    Issues.create('DS', 'Story') {
    setSummary('My Issue Summary from SR Console')
    setPriority('High')
    setDescription('Some Demo Description')
    setAssignee('admin005')
    setLabels('Demo')
    setDueDate('08/March/23')
    setCustomFieldValue('Mac or PC','MAc')
    }

///Update Issue
def issue = Issues.getByKey('DS-26')
  
issue.update {
    setSummary('an updated summary')
    setDescription('hello *world*')
}

//Append Update
def issue = Issues.getByKey('DS-1')
issue.update {
    setDescription {
        append ('Text to the End')
    }
}
//append('{color:#FF0000}Test{color}')

def issue = Issues.getByKey('DS-1')
issue.update {
    setCustomFieldValue('PC equipment List') {
        add('Docking Station')
    }
}

//Set Due Date 7 days ahead 
def issue = Issues.getByKey('DS-1')

issue.update {
    setDueDate {
        set(get().plusDays(7))
    }
}


//// New Project    
Projects.create("DPS", "Demo Project Scrum") {
    projectLead = 'admin'
    projectType = "Scrum"
    description = "This is a new project!"
    url = "https://ProjectFlow.co.uk"
    setDefaultAssigneeToProjectLead()
    avatarId = 10001
}

//restrict the comment visibility to a group
Issues.getByKey('DS-1').addComment('My group restricted comment') {
    groupRestriction = 'jira-administrators'
}

//restrict the comment visibility to a project role
Issues.getByKey('DS-1').addComment('My role restricted comment') {
    projectRoleRestriction = 'Administrators'
}
