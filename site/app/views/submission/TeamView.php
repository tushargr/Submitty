<?php

namespace app\views\submission;

use app\libraries\FileUtils;
use app\views\AbstractView;

class TeamView extends AbstractView {

    /**
    * Show team management page
    * @param \app\models\Gradeable $gradeable
    * @param \app\models\Team[] $teams
    * @return string
    */
    public function showTeamPage($gradeable, $teams, $lock, $users_seeking_team) {
        $site_url = $this->core->getConfig()->getSiteUrl();
        $semester = $this->core->getConfig()->getSemester();
        $course = $this->core->getConfig()->getCourse();
        $user_id = $this->core->getUser()->getId();
        
        $team = $gradeable->getTeam();
        $return = <<<HTML
<div class="content">
    <h2>Manage Team For: {$gradeable->getName()}</h2>
HTML;
    
    if ($lock) {
        if ($team === null) {
        $return .= <<<HTML
    <p class="red-message">
    Teams are now locked for this assignment.<br>
    You can create a new team of 1 or accept an invitation sent before teams were locked.<br>
    Contact your instructor to make further changes to your team.
    </p><br />
HTML;
        }
        else {
            $return .= <<<HTML
    <p class="red-message">
    Teams are now locked for this assignment.<br>
    Contact your instructor to make changes to your team.
    </p><br />
HTML;
        }
    }

    //Top content box, has team
    if ($team !== null) {

        //List team members
        $return .= <<<HTML
    <h3>Your Team:</h3> <br />
HTML;
        foreach ($team->getMembers() as $teammate) {
            $teammate = $this->core->getQueries()->getUserById($teammate);
            $return .= <<<HTML
        <span>&emsp;{$teammate->getDisplayedFirstName()} {$teammate->getLastName()} ({$teammate->getId()}) - {$teammate->getEmail()}</span> <br />
HTML;
        }
        //Team invitations status
        if (count($team->getInvitations()) !== 0) {
            $return .= <<<HTML
    <br />
    <h3>Pending Invitations:</h3> <br />
HTML;
            foreach ($team->getInvitations() as $invited) {
                if ($lock) {
                    $return .= <<<HTML
    <span>&emsp;{$invited}</span> <br />
HTML;
                }
                else {
                    $return .= <<<HTML
    <form action="{$this->core->buildUrl(array('component' => 'student', 'gradeable_id' => $gradeable->getId(), 'page' => 'team', 'action' => 'cancel'))}" method="post">
        <input type="hidden" name="cancel_id" value={$invited} />
        &emsp;{$invited}: <input type="submit" value = "Cancel" class="btn btn-danger" />
    </form><br />
HTML;
                }
            }
        }
        if ($gradeable->getIsRepository()) {
            if (strpos($gradeable->getSubdirectory(), '://') !== false || substr($gradeable->getSubdirectory(), 0, 1) === '/') {
                $vcs_path = $gradeable->getSubdirectory();
            }
            else {
                if (strpos($this->core->getConfig()->getVcsBaseUrl(), '://')) {
                    $vcs_path = rtrim($this->core->getConfig()->getVcsBaseUrl(), '/') . '/' . $gradeable->getSubdirectory();
                }
                else {
                    $vcs_path = FileUtils::joinPaths($this->core->getConfig()->getVcsBaseUrl(), $gradeable->getSubdirectory());
                }
            }
            $repo = $vcs_path;

            $repo = str_replace('{$gradeable_id}', $gradeable->getId(), $repo);
            $repo = str_replace('{$user_id}', $this->core->getUser()->getId(), $repo);
            $repo = str_replace(FileUtils::joinPaths($this->core->getConfig()->getSubmittyPath(), 'vcs'),
                $this->core->getConfig()->getVcsUrl(), $repo);
            $repo = str_replace('{$team_id}', $team->getId(), $repo);
            $return .= <<<HTML
    <br />
    <h3>To access your Team Repository:</h3>
    <span>
<em>Note: There may be a delay before your repository is prepared, please refer to assignment instructions.</em>
    <br />
    <br />

<samp>git  clone  {$repo}  SPECIFY_TARGET_DIRECTORY</samp>
<p>

    </span> <br />
HTML;
        }
    }

    //Top content box, no team
    else {
        $return .= <<<HTML
    <h4>You are not on a team.</h4> <br />
HTML;
    }
    $return .= <<<HTML
</div>
HTML;

    //Bottom content box, has team, teams not locked
    if ($team !== null && !$lock) {
        $return .= <<<HTML
<div class="content">
    <h3>Invite new teammates by their user ID:</h3>
    <br />
    <form action="{$this->core->buildUrl(array('component' => 'student', 'gradeable_id' => $gradeable->getId(), 'page' => 'team', 'action' => 'invitation'))}" method="post">
        <input type="text" name="invite_id" placeholder="User ID" />
        <input type="submit" value = "Invite" class="btn btn-primary" />
    </form>
    <br />
    <button class="btn btn-danger" onclick="location.href='{$this->core->buildUrl(array('component' => 'student', 'gradeable_id' => $gradeable->getId(), 'page' => 'team', 'action' => 'leave_team'))}'">Leave Team</button>
    <button class="btn btn-default" style="float:right" onclick="$('.popup-form').css('display', 'none');$('#users_seeking_team_show').css('display', 'block');">Users Seeking Team/Partner</button>
HTML;
    }

    //Bottom content box, no team
    else if ($team === null) {

        //Invitations received
        $invites_received = array();
        foreach($teams as $t) {
            if ($t->sentInvite($user_id)) {
                $invites_received[] = $t;
            }
        }

        if(count($invites_received) === 0) {
            $return .= <<<HTML
<div class="content">
    <h4>You have not received any invitations.</h4> <br />
HTML;
        }
        else {
            $return .= <<<HTML
<div class="content">
    <h3>Invitations:</h3> <br />
HTML;
            foreach ($invites_received as $invite){
                $return .= <<<HTML
    <form action="{$this->core->buildUrl(array('component' => 'student', 'gradeable_id' => $gradeable->getId(), 'page' => 'team', 'action' => 'accept'))}" method="post">
        <input type="hidden" name="team_id" value={$invite->getId()} />
        &emsp;{$invite->getMemberList()}: <input type="submit" value = "Accept" class="btn btn-success" />
    </form>
    <br />
HTML;
            }
        }

        //Create new team button
        $return .= <<<HTML
    <br />
    <button class="btn btn-primary" onclick="location.href='{$this->core->buildUrl(array('component' => 'student', 'gradeable_id' => $gradeable->getId(), 'page' => 'team', 'action' => 'create_new_team'))}'">Create New Team </button>
HTML;
		if(!(in_array($user_id, $users_seeking_team))){
			$return .= <<<HTML
    &nbsp;or&nbsp;<button class="btn btn-primary" onclick="location.href='{$this->core->buildUrl(array('component' => 'student', 'gradeable_id' => $gradeable->getId(), 'page' => 'team', 'action' => 'seek_team'))}'">Seek Team/Partner </button>
HTML;
		}
		$return .= <<<HTML
	<button class="btn btn-default" style="float:right" onclick="$('.popup-form').css('display', 'none');$('#users_seeking_team_show').css('display', 'block');">Users Seeking Team/Partner</button>
HTML;
    }
    $return .= <<<HTML
</div>
<div class="popup-form" id="users_seeking_team_show" style="width:420px">
	<center><h3>Users seeking team/partner-</h3></center><br />
	<form>
HTML;
	foreach ($users_seeking_team as $user_seeking_team) {
		$return .= <<<HTML
		<center><input class="readonly" type="text" readonly="readonly" value="{$user_seeking_team}" /></center><br />
HTML;
	}
	if (empty($users_seeking_team)) {
		$return .= <<<HTML
		<center>no one seeking team/partner right now</center><br />
HTML;
	}
	$return .= <<<HTML
    <a style="float:right" onclick="$('#users_seeking_team_show').css('display', 'none');" class="btn btn-danger">Back</a>
	</form>
</div>
HTML;
    return $return;
    }
}
